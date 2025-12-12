from insightface.app import FaceAnalysis
import numpy as np
from PIL import Image
import os
import tempfile
from typing import List, Tuple
from services.minio_service import minio_service
from sklearn.metrics.pairwise import cosine_similarity

# Initialize InsightFace (runs on GPU if available)
app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))  # ctx_id = 0 for GPU, -1 for CPU

class FaceVerif:
    def __init__(self):
        pass
    
    def extract_faces(self, image_path):
        """Extract faces from the image"""
        img = Image.open(image_path).convert('RGB')
        img_bgr = np.array(img)[:, :, ::-1]
        faces = app.get(img_bgr)
        
        if faces:
            embeddings = np.array([face['embedding'] for face in faces])
            return embeddings  # already numpy
        else:
            return None
    
    def match_faces(self, selfie_path, image_path):
        """Match faces between two images"""
        try:
            img1 = Image.open(image_path).convert('RGB')
            img2 = Image.open(selfie_path).convert('RGB')
            
            # Detect faces in both images
            faces1 = app.get(np.array(img1)[:, :, ::-1])
            faces2 = app.get(np.array(img2)[:, :, ::-1])
            
            if not faces1 or not faces2:
                return False, 0.0
            
            # Get embeddings for all faces
            embs1 = np.array([f['embedding'] for f in faces1])
            embs2 = np.array([f['embedding'] for f in faces2])
            
            # Calculate similarities between all face pairs
            sim_matrix = cosine_similarity(embs1, embs2)
            max_similarity = sim_matrix.max()  # highest similarity between any pair

            # Cosine similarity ranges from -1 to 1; for ArcFace embeddings, usually 0.2–1.0
            threshold = 0.35  # typical starting point; tune based on your data
            is_match = max_similarity > threshold
            
            return is_match, float(max_similarity)
            
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
            selfie_img = Image.open(selfie_path).convert('RGB')
            selfie_faces = app.get(np.array(selfie_img)[:, :, ::-1])
            
            if not selfie_faces:
                print("No faces detected in selfie")
                return matches
                
            selfie_embs = np.array([f['embedding'] for f in selfie_faces])
            
            # List all files in the bucket
            file_list = minio_service.list_files(bucket_name)
            
            # Temporary directory for downloading images
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_name in file_list:
                    if not any(file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                        continue
                        
                    temp_file_path = os.path.join(temp_dir, file_name)
                    minio_service.download_file(bucket_name, file_name, temp_file_path)
                    
                    bucket_img = Image.open(temp_file_path).convert('RGB')
                    bucket_faces = app.get(np.array(bucket_img)[:, :, ::-1])
                    
                    if not bucket_faces:
                        continue
                        
                    bucket_embs = np.array([f['embedding'] for f in bucket_faces])
                    
                    # Calculate cosine similarities between all face pairs
                    similarities = cosine_similarity(selfie_embs, bucket_embs)
                    max_similarity = similarities.max()
                    
                    if max_similarity > threshold:  # threshold closer to 1 means more similar
                        matches.append((file_name, float(max_similarity)))
                        
        except Exception as e:
            print(f"Error in match_selfie_with_bucket_images: {e}")
            
        # Sort matches by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches