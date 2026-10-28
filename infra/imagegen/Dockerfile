# R-801: خادم توليد الصور الذاتي (stable-diffusion.cpp، معالج فقط) — يُبنى ويُشغَّل على آلة Fly خاصة.
FROM python:3.11-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*
# لا تعليمات خاصة بمعالج البناء (قد يحوي AVX-512 غير الموجود على آلات Fly) — AVX2/FMA/F16C فقط
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON" \
    CMAKE_BUILD_PARALLEL_LEVEL=4
RUN pip wheel --no-cache-dir -w /wheels stable-diffusion-cpp-python==0.4.7

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
COPY server.py /app/server.py
ENV PORT=8080 IMAGEGEN_MODEL_PATH=/models/sd_turbo-f16-q8_0.gguf
EXPOSE 8080
CMD ["python", "/app/server.py"]
