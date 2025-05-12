import os
import json
import boto3
import torch
import base64
import numpy as np
from PIL import Image
from facenet_pytorch import InceptionResnetV1

q_service = boto3.client('sqs')

weights_path = '/var/task/resnetV1_video_weights.pt'  
temp_img_path = '/tmp/face.jpg'
resp_queue_url = ""
req_queue_url = ""

#Face recognition code taken from the github repo given in project documentation
class face_recognition:

    def face_recognition_func(self, model_wt_path, face_img_path):
        
        # # Step 1: Load image as PIL
        face_pil = Image.open(face_img_path).convert("RGB")
        #key      = os.path.splitext(os.path.basename(face_img_path))[0].split(".")[0]

        # Step 2: Convert PIL to NumPy array (H, W, C) in range [0, 255]
        face_numpy = np.array(face_pil, dtype=np.float32) / 255.0
        
        # Step 3: Normalize values to [0,1] and transpose to (C, H, W)
        #face_numpy /= 255.0  # Normalize to range [0,1]
        
        # Convert (H, W, C) → (C, H, W)
        face_numpy = np.transpose(face_numpy, (2, 0, 1))
        
        # Step 4: Convert NumPy to PyTorch tensor
        face_tensor = torch.tensor(face_numpy, dtype=torch.float32)

        saved_data = torch.load(model_wt_path) # loading resnetV1_video_weights.pt
        
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval()

        #if face_tensor != None:
        emb = self.resnet(face_tensor.unsqueeze(0)).detach() # detech is to make required gradient false
        embedding_list  = saved_data[0]  # getting embedding data
        name_list       = saved_data[1]  # getting list of names
        dist_list       = []  # list of matched distances, minimum distance is used to identify the person
            
        for idx, emb_db in enumerate(embedding_list):
            dist = torch.dist(emb, emb_db).item()
            dist_list.append(dist)

        if dist_list:
            idx_min = dist_list.index(min(dist_list))
            return name_list[idx_min]
        else:
            print(f"not recognised")
            return "Unknown"

def recognition_lambda_handler(event, context):
    recog = face_recognition()
    
    for record in event['Records']:
        receipt_handle = record.get('receiptHandle')
        try:
            message = json.loads(record['body'])
            request_id = message['request_id']
            filename = message['filename']
            content = message['content']
            print(f"req_id:{request_id}")
            
            print(f"start decoding")
            img_decode = base64.b64decode(content)
            with open(temp_img_path, 'wb') as f:
                f.write(img_decode)
            print(f"decodeing saved, start recognition")

            ans = recog.face_recognition_func(model_wt_path=weights_path, face_img_path= temp_img_path)
            print(f"recognition complete, ans: {ans}")
            
            ans_message = {'request_id': request_id,'result': ans}

            q_service.send_message(
                QueueUrl= resp_queue_url,
                MessageBody=json.dumps(ans_message)
            )
            print(f"ans sent to resp queue")

            q_service.delete_message(
                QueueUrl= req_queue_url,
                ReceiptHandle=receipt_handle
            )

        except Exception as e:
            print(f"img not recognised {e}")

    return {'statusCode': 200, 'body': 'done processing'}
