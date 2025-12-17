// Selfie capture variables
let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let capturedImage = document.getElementById('capturedImage');
let ctx = canvas.getContext('2d');
let stream = null;

// DOM elements for selfie functionality
const startCameraBtn = document.getElementById('startCameraBtn');
const captureBtn = document.getElementById('captureBtn');
const retakeBtn = document.getElementById('retakeBtn');
const submitSelfieBtn = document.getElementById('submitSelfieBtn');
const capturedImageContainer = document.getElementById('capturedImageContainer');
const personNameInput = document.getElementById('personName');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsContainer = document.getElementById('resultsContainer');
const matchesList = document.getElementById('matchesList');
const eventIdInput = document.getElementById('eventId');
const viewAllImagesBtn = document.getElementById('viewAllImagesBtn');
const allImagesContainer = document.getElementById('allImagesContainer');
const allImagesList = document.getElementById('allImagesList');
const backToMatchesBtn = document.getElementById('backToMatchesBtn');

// Function to start the timer
function startTimer() {
  // Timer functionality removed as requested
}

// Start timer when the email form is displayed
window.onload = function() {
  const emailForm = document.getElementById('emailForm');
  
  // Handle success toast
  const successToast = document.getElementById('successToast');
  if (successToast) {
    // Hide the toast after 5 seconds
    setTimeout(function() {
      successToast.style.display = 'none';
      // Then show the search form
      showSearchForm();
    }, 5000);
  }
};

function setMediaNumber(type) {
  const numberInput = document.getElementById('media_number');
  const hiddenInput = document.getElementById(type + '-number-input');
  if (numberInput && hiddenInput) {
    hiddenInput.value = numberInput.value;
  }
}

function showSearchForm() {
  // Hide all elements related to media found
  const mediaFoundMessage = document.getElementById('mediaFoundMessage');
  const downloadLink = document.getElementById('downloadLink');
  const emailPrompt = document.getElementById('emailPrompt');
  const emailForm = document.getElementById('emailForm');
  const backButtonContainer = document.getElementById('backButtonContainer');
  const successToast = document.getElementById('successToast');
  
  if (mediaFoundMessage) mediaFoundMessage.style.display = 'none';
  if (downloadLink) downloadLink.style.display = 'none';
  if (emailPrompt) emailPrompt.style.display = 'none';
  if (emailForm) emailForm.style.display = 'none';
  if (backButtonContainer) backButtonContainer.style.display = 'none';
  if (successToast) successToast.style.display = 'none';
  
  // Show the search form
  const searchForm = document.getElementById('searchForm');
  if (searchForm) searchForm.style.display = 'block';
  
  // Clear the input field
  const mediaNumberInput = document.getElementById('media_number');
  if (mediaNumberInput) mediaNumberInput.value = '';
}

// Selfie capture functions
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    startCameraBtn.classList.add('hidden');
    captureBtn.classList.remove('hidden');
  } catch (err) {
    console.error("Error accessing camera: ", err);
    alert("Could not access the camera. Please ensure you've granted permission and that your camera is working.");
  }
}

function capturePhoto() {
  // Draw the current video frame to the canvas
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  // Convert to image data
  const imageData = canvas.toDataURL('image/png');
  capturedImage.src = imageData;
  
  // Show the captured image and hide the video
  video.classList.add('hidden');
  capturedImageContainer.classList.remove('hidden');
  
  // Update button visibility
  captureBtn.classList.add('hidden');
  retakeBtn.classList.remove('hidden');
  submitSelfieBtn.classList.remove('hidden');
}

function retakePhoto() {
  // Hide the captured image and show the video
  video.classList.remove('hidden');
  capturedImageContainer.classList.add('hidden');
  resultsContainer.classList.add('hidden');
  allImagesContainer.classList.add('hidden');
  
  // Update button visibility
  captureBtn.classList.remove('hidden');
  retakeBtn.classList.add('hidden');
  submitSelfieBtn.classList.add('hidden');
}

async function submitSelfie() {
  const name = personNameInput.value.trim();
  if (!name) {
    alert("Please enter your name");
    return;
  }
  
  // Show loading indicator
  loadingIndicator.classList.remove('hidden');
  resultsContainer.classList.add('hidden');
  allImagesContainer.classList.add('hidden');
  
  try {
    // Get image data from canvas
    const imageData = canvas.toDataURL('image/png');
    
    // Get event ID if available
    const eventId = eventIdInput ? eventIdInput.value : null;
    
    // Check if we have an event
    if (!eventId) {
      alert("No event selected. Please access this page with a valid event.");
      // Hide loading indicator
      loadingIndicator.classList.add('hidden');
      return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('selfie_data', imageData);
    formData.append('person_name', name);
    if (eventId) {
      formData.append('event_id', eventId);
    }
    
    // Send to server
    const response = await fetch('/download/selfie-match', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    // Hide loading indicator
    loadingIndicator.classList.add('hidden');
    
    if (result.success) {
      // Display results
      displayMatches(result.matches);
    } else {
      alert("Error: " + result.error);
    }
  } catch (error) {
    // Hide loading indicator
    loadingIndicator.classList.add('hidden');
    console.error("Error submitting selfie: ", error);
    alert("An error occurred while processing your selfie. Please try again.");
  }
}

function displayMatches(matches) {
  // Clear previous results
  matchesList.innerHTML = '';
  
  if (matches.length === 0) {
    matchesList.innerHTML = '<p class="col-span-2 text-center">No matching photos found.</p>';
  } else {
    // Display matches with actual images and functional view buttons
    matches.forEach(match => {
      const matchElement = document.createElement('div');
      matchElement.className = 'border rounded p-2 text-center';
      matchElement.innerHTML = `
        <div class="bg-gray-200 border-2 border-dashed rounded-xl w-full h-32 mx-auto flex items-center justify-center overflow-hidden">
          <img src="/download/image/${match.id}" alt="Matched photo" class="w-full h-full object-cover" onerror="this.parentElement.innerHTML='<div class=\\'text-gray-500\\'>Image not available</div>'">
        </div>
        <p class="text-sm mt-1">Similarity: ${(match.similarity * 100).toFixed(1)}%</p>
        <button class="mt-2 px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 view-photo-btn" data-photo-id="${match.id}">
          View Photo
        </button>
      `;
      matchesList.appendChild(matchElement);
    });
    
    // Add event listeners to view photo buttons
    document.querySelectorAll('.view-photo-btn').forEach(button => {
      button.addEventListener('click', function() {
        const photoId = this.getAttribute('data-photo-id');
        window.open(`/download/image/${photoId}`, '_blank');
      });
    });
  }
  
  // Show results container
  resultsContainer.classList.remove('hidden');
  allImagesContainer.classList.add('hidden');
}

async function loadAllImages() {
  const eventId = eventIdInput ? eventIdInput.value : null;
  if (!eventId) {
    alert("No event selected. Please access this page with a valid event.");
    return;
  }
  
  // Show loading indicator
  loadingIndicator.classList.remove('hidden');
  resultsContainer.classList.add('hidden');
  allImagesContainer.classList.add('hidden');
  
  try {
    const response = await fetch(`/download/all-images/${eventId}`);
    const result = await response.json();
    
    // Hide loading indicator
    loadingIndicator.classList.add('hidden');
    
    if (result.success) {
      displayAllImages(result.photos);
    } else {
      alert("Error: " + result.error);
    }
  } catch (error) {
    // Hide loading indicator
    loadingIndicator.classList.add('hidden');
    console.error("Error loading all images: ", error);
    alert("An error occurred while loading images. Please try again.");
  }
}

function displayAllImages(photos) {
  // Clear previous results
  allImagesList.innerHTML = '';
  
  if (photos.length === 0) {
    allImagesList.innerHTML = '<p class="col-span-2 text-center">No images found for this event.</p>';
  } else {
    // Display all images
    photos.forEach(photo => {
      const photoElement = document.createElement('div');
      photoElement.className = 'border rounded p-2 text-center';
      photoElement.innerHTML = `
        <div class="bg-gray-200 border-2 border-dashed rounded-xl w-full h-32 mx-auto flex items-center justify-center overflow-hidden">
          <img src="/download/image/${photo.id}" alt="Event photo" class="w-full h-full object-cover" onerror="this.parentElement.innerHTML='<div class=\\'text-gray-500\\'>Image not available</div>'">
        </div>
        <button class="mt-2 px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 view-photo-btn" data-photo-id="${photo.id}">
          View Photo
        </button>
      `;
      allImagesList.appendChild(photoElement);
    });
    
    // Add event listeners to view photo buttons
    document.querySelectorAll('#allImagesList .view-photo-btn').forEach(button => {
      button.addEventListener('click', function() {
        const photoId = this.getAttribute('data-photo-id');
        window.open(`/download/image/${photoId}`, '_blank');
      });
    });
  }
  
  // Show all images container
  allImagesContainer.classList.remove('hidden');
  resultsContainer.classList.add('hidden');
}

// Event listeners for selfie functionality
if (startCameraBtn) startCameraBtn.addEventListener('click', startCamera);
if (captureBtn) captureBtn.addEventListener('click', capturePhoto);
if (retakeBtn) retakeBtn.addEventListener('click', retakePhoto);
if (submitSelfieBtn) submitSelfieBtn.addEventListener('click', submitSelfie);

// Event listeners for viewing all images
if (viewAllImagesBtn) viewAllImagesBtn.addEventListener('click', loadAllImages);
if (backToMatchesBtn) backToMatchesBtn.addEventListener('click', function() {
  resultsContainer.classList.remove('hidden');
  allImagesContainer.classList.add('hidden');
});