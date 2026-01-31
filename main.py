from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from googlesearch import search  # Esta importação funciona com googlesearch-python
import uvicorn
import logging
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Busca Médica Especializada")

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
        "bvsms.saude.gov.br",
        "www.gov.br/conitec/pt-br",
        "www.scielo.br",
        "amb.org.br",
    ]

    # Tentativa de busca refinada
    search_query = f"{query} site:({' OR '.join(sites)})"
    logger.info(f"Buscando por: {search_query}")

    try:
        # A biblioteca googlesearch-python retorna um gerador
        # Usamos list() para pegar os resultados e tratamos possíveis erros de rede
        search_results = list(search(search_query, num_results=3, lang="pt"))
        
        # Se não encontrar nada com os sites, tenta busca aberta
        if not search_results:
            logger.info("Nenhum resultado nos sites específicos, tentando busca aberta.")
            search_results = list(search(query, num_results=3, lang="pt"))

        if not search_results:
            return {"source": "N/A", "content": "Nenhuma informação encontrada."}

        # Tenta processar o primeiro resultado válido
        for url in search_results:
            try:
                logger.info(f"Processando URL: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Limpeza agressiva de tags irrelevantes
                for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form", "noscript"]):
                    tag.decompose()

                # Extração de texto limpo
                lines = (line.strip() for line in soup.get_text(separator='\n').splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                if len(text) > 100:  # Garante que pegamos conteúdo real
                    return {
                        "source": url,
                        "content": text[:5000]
                    }
            except Exception as e:
                logger.error(f"Erro ao processar {url}: {e}")
                continue

        return {"source": "N/A", "content": "Não foi possível extrair conteúdo útil dos resultados encontrados."}

    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        # Retornamos uma mensagem amigável em vez de travar
        return {"source": "Erro", "content": f"Ocorreu um erro na busca: {str(e)}"}

if __name__ == "__main__":
    # Render fornece a porta na variável de ambiente PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
