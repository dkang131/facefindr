// Function to show toast notifications
function showToast(message, isSuccess = true) {
  const toastContainer = document.getElementById('toast-container');
  
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast ${isSuccess ? 'success' : 'error'} show`;
  toast.textContent = message;
  
  // Add toast to container
  toastContainer.appendChild(toast);
  
  // Remove toast after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      toastContainer.removeChild(toast);
    }, 300);
  }, 3000);
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  
  try {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);
    
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: formData,
      redirect: 'follow'  // Let the browser follow redirects
    });
    
    // If we get here, it means we didn't get redirected (probably an error)
    if (response.ok) {
      // Success - we should have been redirected
      window.location.href = '/cms/dashboard';
    } else {
      // Try to parse error response
      try {
        const data = await response.json();
        const errorMessage = data.message || data.errors?.message || 'Login failed! Please check your credentials and try again.';
        showToast(errorMessage, false);
      } catch (parseError) {
        // If we can't parse JSON, show a generic error
        showToast('Login failed! Please check your credentials and try again.', false);
      }
    }
  } catch (error) {
    showToast('An error occurred during login.', false);
    console.error('Login error:', error);
  }
});