// Modal functions
function openUploadModal() {
  document.getElementById('uploadModal').classList.remove('hidden');
  document.getElementById('uploadModal').classList.add('flex');
}

function closeUploadModal() {
  document.getElementById('uploadModal').classList.add('hidden');
  document.getElementById('uploadModal').classList.remove('flex');
}

// Edit modal functions
function openEditModal(eventId) {
  // Set the form action to the edit endpoint
  document.getElementById('editEventForm').action = '/cms/edit-event/' + eventId;
  // Set the event ID in the hidden input
  document.getElementById('edit_event_id').value = eventId;
  // Show the edit modal
  document.getElementById('editModal').classList.remove('hidden');
  document.getElementById('editModal').classList.add('flex');
}

function closeEditModal() {
  document.getElementById('editModal').classList.add('hidden');
  document.getElementById('editModal').classList.remove('flex');
}

// Delete function
function deleteEvent(eventId) {
  if (confirm('Are you sure you want to delete this event? This action cannot be undone.')) {
    // Create a form to submit the delete request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/cms/delete-event/' + eventId;
    
    // Add CSRF token if needed
    // const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    // const csrfInput = document.createElement('input');
    // csrfInput.type = 'hidden';
    // csrfInput.name = 'csrf_token';
    // csrfInput.value = csrfToken;
    // form.appendChild(csrfInput);
    
    document.body.appendChild(form);
    form.submit();
  }
}