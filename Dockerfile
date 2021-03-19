###### Minimal image with base system requirements for most stages
FROM docker.io/ubuntu:16.04 as minimal
MAINTAINER eduNEXT <contact@edunext.co>

RUN apt update && \
    apt install -y build-essential curl git language-pack-en
ENV LC_ALL en_US.UTF-8

###### Install python with pyenv in /opt/pyenv and create virtualenv in /openedx/venv
FROM minimal as python
# https://github.com/pyenv/pyenv/wiki/Common-build-problems#prerequisites
RUN apt update && \
    apt install -y libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev python-openssl git
ARG PYTHON_VERSION=3.5.9
ENV PYENV_ROOT /opt/pyenv
RUN git clone https://github.com/pyenv/pyenv $PYENV_ROOT --branch v1.2.18 --depth 1
RUN $PYENV_ROOT/bin/pyenv install $PYTHON_VERSION
RUN $PYENV_ROOT/versions/$PYTHON_VERSION/bin/pyvenv /openedx/venv


###### Install python requirements in virtualenv
FROM python as python-requirements

WORKDIR /openedx/edx-platform

ENV PATH /openedx/venv/bin:${PATH}
ENV VIRTUAL_ENV /openedx/venv/

# Install requirements
COPY setup.py setup.py
COPY common common
COPY openedx openedx
COPY lms lms
COPY cms cms
COPY requirements/pip.txt requirements/pip.txt
COPY requirements/edx/base.txt requirements/edx/base.txt
RUN pip install -r requirements/pip.txt
RUN pip install -r requirements/edx/base.txt

# Install private requirements
ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

# make sure your domain is accepted
RUN touch /root/.ssh/known_hosts
RUN ssh-keyscan bitbucket.org >> /root/.ssh/known_hosts

# install packages
RUN pip install git+ssh://git@bitbucket.org/edunext/eox-manage.git@v0.8.0#egg=eox-manage==0.8.0
RUN pip install git+ssh://git@bitbucket.org/edunext/eox-taylor.git@v0.5.1#egg=eox-taylor==0.5.1
RUN pip install git+ssh://git@bitbucket.org/edunext/eox-support.git@v1.0.0#egg=eox-support==1.0.0

# Install whitenoise, for serving static assets
RUN pip install "whitenoise==5.1.0"


###### Install nodejs with nodeenv in /openedx/nodeenv
FROM python-requirements as nodejs-requirements

ENV PATH /openedx/nodeenv/bin:${PATH}
ENV PATH ./node_modules/.bin:${PATH}

# Copy just JS requirements and install them.
COPY package.json package.json
COPY package-lock.json package-lock.json
RUN nodeenv /edx/app/edxapp/nodeenv --node=12.11.1 --prebuilt
RUN npm set progress=false && npm install

####### edxapp base image ######
FROM minimal as edxapp-base

# Install system requirements
RUN apt update && \
    apt install -y gettext gfortran graphviz graphviz-dev libffi-dev libfreetype6-dev libgeos-dev libjpeg8-dev liblapack-dev libmysqlclient-dev libpng12-dev libsqlite3-dev libxmlsec1-dev lynx ntp pkg-config rdfind && \
    rm -rf /var/lib/apt/lists/*

COPY --from=python /opt/pyenv /opt/pyenv
COPY --from=python-requirements /openedx/venv /openedx/venv
COPY --from=nodejs-requirements /openedx/nodeenv /openedx/nodeenv
COPY --from=nodejs-requirements /openedx/edx-platform/node_modules /openedx/edx-platform/node_modules

WORKDIR /openedx/edx-platform
# Copy over remaining code.
# We do this as late as possible so that small changes to the repo don't bust
# the requirements cache.
COPY . .

# RUN mkdir -p /edx/etc/
# ENV PATH /edx/app/edxapp/edx-platform/bin:${PATH}
# ENV CONFIG_ROOT /edx/etc/
# ENV SETTINGS production

# ENV LMS_CFG /edx/etc/lms.yml
# ENV STUDIO_CFG /edx/etc/studio.yml
# COPY lms/devstack.yml /edx/etc/lms.yml
# COPY cms/devstack.yml /edx/etc/studio.yml
