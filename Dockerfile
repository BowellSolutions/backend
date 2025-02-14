# Copyright (c) 2022 Adam Lisichin, Hubert Decyusz, Wojciech Nowicki, Gustaw Daczkowski
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
FROM python:3.9.6-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies and required packages to compile some of them
COPY requirements.txt /app
RUN  \
    apk update && \
    apk upgrade && \
    apk add bash postgresql-libs libressl-dev musl-dev libffi-dev cargo && \
    apk add --virtual .build-deps gcc postgresql-dev && \
    pip3 install --upgrade pip -r requirements.txt && \
    apk --purge del .build-deps

# Add the rest of the code
COPY . /app

# Make port 8000 available for the app
EXPOSE 8000

# Be sure to use 0.0.0.0 for the host within the Docker container,
# otherwise the browser won't be able to find it
RUN ["chmod", "+x", "/app/scripts/entrypoint-dev.sh"]
ENTRYPOINT [ "/app/scripts/entrypoint-dev.sh" ]
