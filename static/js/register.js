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

document.getElementById('register-btn').addEventListener('click', async () => {
  const masterToken = document.getElementById('master-token').value;
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  const role = document.getElementById('role').value;

  if (!masterToken) {
    showToast('Master token is required!', false);
    return;
  }

  if (password !== confirmPassword) {
    showToast('Passwords do not match!', false);
    return;
  }

  try {
    // Use secure admin registration endpoint
    const response = await fetch('/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${masterToken}`
      },
      body: JSON.stringify({ email, password, role })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showToast('Admin registered successfully!');
      document.getElementById('master-token').value = '';
      document.getElementById('email').value = '';
      document.getElementById('password').value = '';
      document.getElementById('confirm-password').value = '';
    } else {
      // Show detailed error message from server
      const errorMessage = data.message || data.detail || 'Registration failed! Please check your inputs and try again.';
      showToast(errorMessage, false);
    }
  } catch (error) {
    showToast('An error occurred during registration.', false);
    console.error('Registration error:', error);
  }
});