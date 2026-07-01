FROM ghcr.io/berriai/litellm:main
# Continue usa stream:true; sin esta dependencia LiteLLM puede devolver 500 en streaming con Ollama.
RUN pip install --no-cache-dir async_generator
