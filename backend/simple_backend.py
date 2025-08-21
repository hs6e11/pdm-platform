from fastapi import FastAPI
import uvicorn
import time

app = FastAPI(title='PdM Platform API', version='1.0.0')

@app.get('/health')
def health():
    return {'status': 'healthy', 'timestamp': time.time(), 'version': '1.0.0'}

@app.get('/')
def root():
    return {'service': 'PdM Platform API', 'version': '1.0.0', 'status': 'operational'}

@app.get('/docs')
def docs_redirect():
    return {'message': 'API documentation available at /docs'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
