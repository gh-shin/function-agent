import os
import io
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pymongo import MongoClient
import pandas as pd

load_dotenv()

app = FastAPI(
    title="CSV Embedding Service",
    description="CSV 파일 임베딩 및 MongoDB 저장 API",
)


openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


try:
    mongo_client = MongoClient(os.getenv("MONGODB_URI"))
    db = mongo_client["testdb"] 
    collection = db["testcollection"] 
except Exception as e:
    mongo_client = None


# --- 2. FastAPI 엔드포인트 정의 ---

@app.post("/upload-and-embed/")
async def create_embeddings_from_csv(file: UploadFile = File(...)):
    """
    CSV 파일을 업로드받아 각 행을 임베딩하고 MongoDB에 저장합니다.

    - **file**: 업로드할 CSV 파일.
    """


    if not mongo_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB connection is not available."
        )

    if file.content_type != "text/csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV 파일만 업로드 가능합니다. (Received: {file.content_type})"
        )

    try:
        contents_bytes = await file.read()
        contents_str = contents_bytes.decode("utf-8")

        df = pd.read_csv(io.StringIO(contents_str))

        df = df.where(pd.notna(df), None)

        documents = df.to_dict(orient="records")

        if not documents:
            return {"message": "CSV file is empty.", "documents_inserted": 0}

        texts_to_embed = [json.dumps(doc, ensure_ascii=False) for doc in documents]

        embedding_response = await openai_client.embeddings.create(
            model="text-embedding-3-small", 
            input=texts_to_embed
        )



        documents_to_insert = []
        for i, doc in enumerate(documents):
            doc['embedding'] = embedding_response.data[i].embedding
            doc['source_file'] = file.filename
            documents_to_insert.append(doc)


        result = collection.insert_many(documents_to_insert)

        return {
            "message": "File processed and embedded successfully.",
            "filename": file.filename,
            "documents_inserted": len(result.inserted_ids)
        }

    except pd.errors.ParserError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse the CSV file. Please check the file format."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/")
async def root():
    return {"message": "root 공백 함수"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)