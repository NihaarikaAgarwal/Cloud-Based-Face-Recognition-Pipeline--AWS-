from flask import Flask, request
import boto3
import threading
import time
import os

app = Flask(__name__)

REGION = "us-east-1"
ASU_ID = ""
S3_INPUT_BUCKET = f"{ASU_ID}-in-bucket"
SQS_REQUEST_QUEUE = f"{ASU_ID}-req-queue"
SQS_RESPONSE_QUEUE = f"{ASU_ID}-resp-queue"

s3 = boto3.client('s3', region_name=REGION)
sqs = boto3.client('sqs', region_name=REGION)

response_cache = {}              
response_conditions = {}         
response_lock = threading.Lock() 

def poll_response_queue():
    
    print("Polling thread started.")
    response_queue_url = sqs.get_queue_url(QueueName=SQS_RESPONSE_QUEUE)['QueueUrl']

    while True:
        try:
            msgs = sqs.receive_message(
                QueueUrl=response_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
                VisibilityTimeout=10
            )

            if 'Messages' in msgs:
                for msg in msgs['Messages']:
                    body = msg['Body']
                    receipt_handle = msg['ReceiptHandle']

                    if ':' in body:
                        image_id, _ = body.split(':', 1)

                        with response_lock:
                            response_cache[image_id] = body
                            condition = response_conditions.get(image_id)

                        if condition:
                            with condition:
                                condition.notify_all()

                        sqs.delete_message(
                            QueueUrl=response_queue_url,
                            ReceiptHandle=receipt_handle
                        )

        except Exception as e:
            print(f" Error in polling thread: {str(e)}")

        time.sleep(1)

@app.route("/", methods=["POST"])
def handle_request():
    if 'inputFile' not in request.files:
        return "No inputFile provided", 400

    file = request.files['inputFile']
    file_name = file.filename
    base_name = os.path.splitext(file_name)[0]

    try:
        s3.upload_fileobj(file, S3_INPUT_BUCKET, file_name)

        req_url = sqs.get_queue_url(QueueName=SQS_REQUEST_QUEUE)['QueueUrl']
        sqs.send_message(QueueUrl=req_url, MessageBody=file_name)

        timeout = 120
        start_time = time.time()
        condition = threading.Condition()

        with response_lock:
            response_conditions[base_name] = condition

        with condition:
            while True:
                with response_lock:
                    if base_name in response_cache:
                        result = response_cache.pop(base_name)
                        return result, 200

                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                if remaining <= 0:
                    return "Timed out waiting for response", 504

                condition.wait(timeout=remaining)

    except Exception as e:
        return f"Error processing request: {str(e)}", 500

    finally:
        with response_lock:
            response_cache.pop(base_name, None)
            response_conditions.pop(base_name, None)

if __name__ == "__main__":
    polling_thread = threading.Thread(target=poll_response_queue, daemon=True)
    polling_thread.start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
