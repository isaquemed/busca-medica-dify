from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import uvicorn

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "Ferramenta de Busca Médica Especializada"}

@app.post("/buscar")
def medical_search(request: SearchRequest):
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="A query não pode ser vazia.")

    # Fontes confiáveis selecionadas
    sites_confiaveis = [
        "bvsms.saude.gov.br",
        "www.gov.br/conitec/pt-br",
        "www.scielo.br",
        "amb.org.br",
    ]
    
    search_query = f"{query} site:{' OR site:'.join(sites_confiaveis)}"

    try:
        # Busca no Google (limitado a 1 resultado para rapidez)
        search_results = list(search(search_query, num_results=1, lang="pt-br"))
        
        if not search_results:
            return {"source": "N/A", "content": "Nenhuma informação encontrada nas fontes confiáveis."}

        url = search_results[0]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
            element.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        
        # Limite de caracteres para o Dify
        return {"source": url, "content": text[:4000]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
