# 1. ابدأ من صورة بايثون الرسمية
FROM python:3.10-slim

# 2. تحديث وتثبيت الأدوات الضرورية و Docker
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    --no-install-recommends

# إضافة مفتاح Docker GPG الرسمي
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# إعداد مستودع Docker
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# تثبيت Docker Engine CLI (العميل فقط)
RUN apt-get update && apt-get install -y docker-ce-cli --no-install-recommends

# 3. تثبيت Docker Compose v2 (الأمر: docker compose)
RUN DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker} && mkdir -p $DOCKER_CONFIG/cli-plugins \
    && curl -SL https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose \
    && chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

# 4. إعداد بيئة العمل ونسخ ملفات التطبيق
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 5. تشغيل التطبيق
CMD ["flask", "run", "--host=0.0.0.0"]
