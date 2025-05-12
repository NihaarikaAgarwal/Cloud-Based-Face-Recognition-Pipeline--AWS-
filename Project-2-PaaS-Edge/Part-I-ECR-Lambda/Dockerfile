FROM python:3.8-slim
#FROM amazon/aws-lambda-python:3.8
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

RUN apt-get update && apt-get install -y cmake ca-certificates libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6
RUN python3 -m pip install torch==1.9.0 torchvision==0.10.0 --extra-index-url https://download.pytorch.org/whl/cpu

#Install the requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN python3 -m pip install -r requirements.txt
RUN python3 -c "from facenet_pytorch import MTCNN; MTCNN(keep_all=True, device='cpu'); print('MTCNN weights preloaded')"

RUN mkdir -p /tmp/.cache
ENV TORCH_HOME=/tmp/.cache/torch                   
ENV XDG_CACHE_HOME=/tmp/.cache/torch

# COPY the code and model weights 
COPY resnetV1_video_weights.pt ${LAMBDA_TASK_ROOT}
COPY fd_lambda.py ${LAMBDA_TASK_ROOT}
COPY fr_lambda.py ${LAMBDA_TASK_ROOT}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
#CMD ["face_detection.detection_lambda_handler"]


