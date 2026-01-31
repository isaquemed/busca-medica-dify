from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import uvicorn
import logging
import os
from fastapi.openapi.utils import get_openapi

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Busca Médica Especializada",
    description="Ferramenta de busca médica para o Dify",
    version="1.0.0"
)

# 1. CORREÇÃO DE CORS (Obrigatório para o Dify Cloud/Navegador)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "API de Busca Médica Especializada"}

@app.post("/buscar")
def medical_search(request: SearchRequest):
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="A query não pode ser vazia.")

    # Fontes confiáveis
    sites = [
        "bvms.saude.gov.br",
        "www.gov.br/conitec/pt-br",
        "www.scielo.br",
        "amb.org.br",
    ]
    
    # Lógica de busca (mantida a sua original)
    try:
        search_query = f"site:{' OR site:'.join(sites)} {query}"
        logger.info(f"Iniciando busca: {search_query}")
        search_results = list(search(search_query, num_results=3, lang="pt"))

        if not search_results:
            logger.info("Nenhum resultado nos sites específicos, tentando busca aberta.")
            search_results = list(search(query, num_results=3, lang="pt"))

        if not search_results:
            return {"source": "N/A", "content": "Nenhuma informação encontrada."}

        for url in search_results:
            try:
                logger.info(f"Processando URL: {url}")
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'noscript']):
                    tag.decompose()

                text = soup.get_text(separator=' ').strip()
                if len(text) > 100:
                    return {"source": url, "content": text[:5000]}
            except Exception as e:
                logger.error(f"Erro ao processar {url}: {e}")
                continue

        return {"source": "N/A", "content": "Não foi possível extrair conteúdo útil."}
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return {"source": "Erro", "content": f"Ocorreu um erro na busca: {str(e)}"}

# 2. CORREÇÃO DO ESQUEMA OPENAPI PARA O DIFY
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Força a versão 3.0.0 que o Dify prefere
    openapi_schema["openapi"] = "3.0.0"
    # Adiciona o servidor do Render diretamente no esquema
    openapi_schema["servers"] = [{"url": "https://busca-medica-dify-i4gy.onrender.com"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000 ))
    uvicorn.run(app, host="0.0.0.0", port=port)
