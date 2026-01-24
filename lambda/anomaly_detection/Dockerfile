FROM public.ecr.aws/lambda/python:3.11

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt \
    --target ${LAMBDA_TASK_ROOT} \
    --no-cache-dir

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_function.lambda_handler"]
