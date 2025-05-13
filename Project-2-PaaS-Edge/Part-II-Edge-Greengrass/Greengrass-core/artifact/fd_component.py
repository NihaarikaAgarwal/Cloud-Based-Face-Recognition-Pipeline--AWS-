import os
import json
import base64
import boto3
import numpy as np
from PIL import Image
import io
import pathlib
from facenet_pytorch import MTCNN
from awsiot import mqtt_connection_builder
from awscrt import io as awscrt_io
from awscrt import mqtt
import time

print("started")

region = "us-east-1"
asu_id = ""
thing_name = f"{asu_id}-IoTThing"
mqtt_topic = f"clients/{thing_name}"

req_queue_url = f""
resp_queue_url = f""

imp_file_path = pathlib.Path(__file__).parent
cert_path = os.path.join(imp_file_path, "thingCert.crt")
key_path = os.path.join(imp_file_path, "privKey.key")
ca_path = os.path.join(imp_file_path, "rootCA.pem")
mqtt_endpoint = "a25m3a2g5loxut-ats.iot.us-east-1.amazonaws.com"

q_service = boto3.client('sqs', region_name=region)

#Face detection code taken from the github repo in provided project document
class FaceDetection:
    def __init__(self):
        print("starting model")
        self.mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20, device='cpu')
        temp_image = Image.fromarray(np.uint8(np.random.rand(240, 240, 3) * 255))
        _ = self.mtcnn(temp_image)
        print("model done")

    def face_detection_func(self, img: Image.Image, image_name, output_path="/tmp"):
        try:
            
            # Step-1: Read the image
            if not isinstance(img, Image.Image):
                img = Image.open(img).convert("RGB")
                img = np.array(img)
                img = Image.fromarray(img)

            face, prob = self.mtcnn(img, return_prob=True, save_path=None)

            if face is not None:
                os.makedirs(output_path, exist_ok=True)
                
                face_img = face - face.min()
                face_img = face_img / face_img.max()
                face_img = (face_img * 255).byte().permute(1, 2, 0).numpy()

                # Convert numpy array to PIL Image
                face_pil = Image.fromarray(face_img, mode="RGB")
                face_img_path = os.path.join(output_path, f"{image_name}_face.jpg")

                # Save face image
                face_pil.save(face_img_path)
                print(f"detected face path {face_img_path}")
                return face_img_path
            
            else:
                print("No face detected")
                return None
            
        except Exception as e:
            print(f"error in detection: {e}")
            return None

detector = FaceDetection()

processed_requests = set()

def msg_received(topic, payload, **kwargs):
    print(f"msg received on {topic}")
    try:
        print(f"msg received on {topic} in try")
        message = json.loads(payload.decode())
        request_id = message['request_id']
        filename = message['filename']
        
        if request_id in processed_requests:
            print(f"duplicate {request_id}")

        processed_requests.add(request_id)
        print(f"Processing {request_id}")
        
        encoded_img = message['encoded']
        decoded_img = base64.b64decode(encoded_img)
        img = Image.open(io.BytesIO(decoded_img)).convert("RGB")
        img.load()
        only_filename = os.path.splitext(os.path.basename(filename))[0]

        print("detection started")
        detected_img_path = detector.face_detection_func(img, image_name=only_filename)
        print("detection complete")

        if detected_img_path:
            print("enter if after detection")
            with open(detected_img_path, "rb") as f:
                img_encoded = base64.b64encode(f.read()).decode('utf-8')
                print("conversion done")

            os.remove(detected_img_path)

            msg = {
                'request_id': request_id,
                'filename': filename,
                'face_detected': True,
                'content': img_encoded
            }

            q_service.send_message(
                QueueUrl=req_queue_url,
                MessageBody=json.dumps(msg)
            )
            print("sent to req q")
        else:
            msg = {
                'request_id': request_id,
                'filename': filename,
                'face_detected': False,
                'result': "No face detected"
            }

            q_service.send_message(
                QueueUrl=resp_queue_url,
                MessageBody=json.dumps(msg)
            )
            print("sent to resp q")

    except Exception as e:
        print(f"error in MQTT callback: {e}")

event_loop_group = awscrt_io.EventLoopGroup(1)
host_resolver = awscrt_io.DefaultHostResolver(event_loop_group)
client_bootstrap = awscrt_io.ClientBootstrap(event_loop_group, host_resolver)

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=mqtt_endpoint,
    cert_filepath=cert_path,
    pri_key_filepath=key_path,
    ca_filepath=ca_path,
    client_bootstrap=client_bootstrap,
    client_id="FaceDetectionComponentTLS",
    clean_session=False,
    keep_alive_secs=30
)

print("connecting to mqtt")
connect_future = mqtt_connection.connect()
connect_future.result()
print("connected")

print(f"now topic: {mqtt_topic}")
sub_future, _ = mqtt_connection.subscribe(topic="clients/1233370023-IoTThing", qos=mqtt.QoS.AT_LEAST_ONCE, callback=msg_received)
sub_future.result()

while True:
    time.sleep(60)
    

