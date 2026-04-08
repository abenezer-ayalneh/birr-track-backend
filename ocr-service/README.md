# OCR + LLM Service

Production-ready OCR and LLM microservice for transaction/receipt extraction.

## Folder Structure

```text
ocr-service/
  app/
    main.py
    routes/llm.py
    routes/ocr.py
    services/
      llm_service.py
      parser.py
      prompt_builder.py
      ocr_service.py
      preprocessing.py
    models/request_models.py
    models/response_models.py
  tests/
    test_parser.py
    test_llm_route.py
  Dockerfile
  requirements.txt
```

## Local Run

```bash
cd ocr-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Local LLM Configuration

Set these optional environment variables before starting the service:

```bash
export LLM_MODEL_PATH="models/mistral-7b-instruct.gguf"
export LLM_N_CTX=2048
export LLM_N_THREADS=8
export LLM_N_GPU_LAYERS=0
export LLM_MAX_TOKENS=300
export LLM_TEMPERATURE=0.1
```

## Docker Run (Recommended for VPS)

```bash
cd ocr-service
docker build -t birr-track-ocr .
docker run --rm -p 8000:8000 --name birr-track-ocr birr-track-ocr
```

## Request Examples

```bash
curl -X POST "http://localhost:8000/ocr" \
  -F "file=@/absolute/path/to/receipt.jpg"
```

```bash
curl -X POST "http://localhost:8000/llm/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Commercial Bank of Ethiopia\\nAmount: 1200.50\\nTxn ID: TRX-100\\n2026-04-02 10:15:00"
  }'
```

## Run Tests

```bash
cd ocr-service
python3 -m unittest discover -s tests
```

## Notes

- OCR and LLM models are initialized once at service startup.
- Service is CPU-oriented and suitable for VPS environments.
- Keep this service isolated from the NestJS app for cleaner deployment lifecycle.
