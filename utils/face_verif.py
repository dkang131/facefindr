from ast import In, alias
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image, ImageDraw
import torch
import os
import tempfile
from typing import List, Tuple
from services.minio_service import minio_service

mtcnn = MTCNN(keep_all=True)
resnet = InceptionResnetV1(pretrained='casia-webface').eval()

class FaceVerif:
    def __init__(self, image_path=None, selfie_path=None):
        self.image_path = image_path
        self.selfie_path = selfie_path
        self.image = None
        self.faces = None
        self.face_embeddings = None
        
        if image_path:
            self.image = Image.open(image_path).convert('RGB')
            self.faces = mtcnn(self.image)
            if self.faces is not None:
                self.face_embeddings = resnet(self.faces).detach().numpy()
    
    def extract_faces(self):
        """Extract faces from the selfie image"""
        if not self.selfie_path:
            return None
            
        img = Image.open(self.selfie_path)
        aligned = mtcnn(img)
        if aligned is not None:
            aligned = aligned.unsqueeze(0)
            embeddings = resnet(aligned).detach()
            return embeddings.numpy()
        else:
            return None
    
    def match_faces(self, selfie_path, image_path):
        """Match faces between two images"""
        try:
            img1 = Image.open(image_path)
            img2 = Image.open(selfie_path)
            
            # Detect faces in both images
            faces1 = mtcnn(img1)
            faces2 = mtcnn(img2)
            
            if faces1 is None or faces2 is None:
                return False, 0.0
            
            # Get embeddings for all faces
            embeddings1 = resnet(faces1).detach()
            embeddings2 = resnet(faces2).detach()
            
            # Calculate distances between all face pairs
            min_distance = float('inf')
            for i in range(len(embeddings1)):
                for j in range(len(embeddings2)):
                    distance = (embeddings1[i] - embeddings2[j]).norm().item()
                    min_distance = min(min_distance, distance)
            
            # Return match result and similarity score
            is_match = min_distance < 0.5
            similarity = max(0, 1 - min_distance)  # Convert distance to similarity score
            
            return is_match, similarity
            
        except Exception as e:
            print(f"Error in match_faces: {e}")
            return False, 0.0
    
    def match_selfie_with_bucket_images(self, selfie_path: str, bucket_name: str, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """
        Match a selfie with all images in a MinIO bucket
        
        Args:
            selfie_path: Path to the selfie image
            bucket_name: Name of the MinIO bucket containing images to match against
            threshold: Distance threshold for matching (lower = stricter)
            
        Returns:
            List of tuples containing (image_name, similarity_score) for matches
        """
        matches = []
        
        try:
            # Extract face embedding from selfie
            selfie_img = Image.open(selfie_path)
            selfie_faces = mtcnn(selfie_img)
            
            if selfie_faces is None:
                print("No faces detected in selfie")
                return matches
                
            selfie_embeddings = resnet(selfie_faces).detach()
            
            # List all files in the bucket
            file_list = minio_service.list_files(bucket_name)
            
            # Temporary directory for downloading images
            with tempfile.TemporaryDirectory() as temp_dir:
                # Process each image in the bucket
                for file_name in file_list:
                    try:
                        # Skip non-image files
                        if not any(file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                            continue
                            
                        # Download image to temporary file
                        temp_file_path = os.path.join(temp_dir, file_name)
                        minio_service.download_file(bucket_name, file_name, temp_file_path)
                        
                        # Process the bucket image
                        bucket_img = Image.open(temp_file_path)
                        bucket_faces = mtcnn(bucket_img)
                        
                        if bucket_faces is None:
                            continue
                            
                        # Get embeddings for bucket image faces
                        bucket_embeddings = resnet(bucket_faces).detach()
                        
                        # Compare selfie faces with bucket image faces
                        min_distance = float('inf')
                        for i in range(len(selfie_embeddings)):
                            for j in range(len(bucket_embeddings)):
                                distance = (selfie_embeddings[i] - bucket_embeddings[j]).norm().item()
                                min_distance = min(min_distance, distance)
                        
                        # Check if this is a match
                        if min_distance < threshold:
                            similarity = max(0, 1 - min_distance)
                            matches.append((file_name, similarity))
                            
                    except Exception as e:
                        print(f"Error processing file {file_name}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error in match_selfie_with_bucket_images: {e}")
            
        # Sort matches by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches