// Main JavaScript for Silhouette Card Maker

// Global variables
let pluginFormats = {};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize file upload handlers
    initializeFileUploads();
    
    // Initialize drag and drop
    initializeDragAndDrop();
    
    // Initialize plugin functionality if available
    if (typeof window.pluginFormats !== 'undefined') {
        pluginFormats = window.pluginFormats;
    }
}

// Tab functionality
function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    const targetContent = document.getElementById(tabName);
    if (targetContent) {
        targetContent.classList.add('active');
    }
    
    // Add active class to clicked tab
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

// Plugin functionality
function updatePluginFormats() {
    const gameSelect = document.getElementById('plugin_game');
    const formatSelect = document.getElementById('plugin_format');
    
    if (!gameSelect || !formatSelect) return;
    
    const selectedGame = gameSelect.value;
    
    // Clear existing options
    formatSelect.innerHTML = '<option value="">Select format...</option>';
    
    // Hide all plugin options
    document.querySelectorAll('.plugin-options').forEach(option => {
        option.classList.remove('active');
    });
    
    if (selectedGame && pluginFormats[selectedGame]) {
        // Add formats for selected game
        pluginFormats[selectedGame].forEach(format => {
            const option = document.createElement('option');
            option.value = format;
            option.textContent = format.toUpperCase().replace('_', ' ');
            formatSelect.appendChild(option);
        });
        
        // Show plugin-specific options
        const optionsDiv = document.getElementById(selectedGame + '_options');
        if (optionsDiv) {
            optionsDiv.classList.add('active');
        }
    }
}

// File upload functionality
function initializeFileUploads() {
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            updateFileUploadFeedback(this);
        });
    });
}

function updateFileUploadFeedback(input) {
    const count = input.files.length;
    const helpText = input.parentNode.querySelector('.help-text');
    
    if (count > 0 && helpText) {
        const originalText = helpText.dataset.original || helpText.textContent;
        helpText.dataset.original = originalText;
        helpText.innerHTML = `${originalText} <strong>(${count} file${count === 1 ? '' : 's'} selected)</strong>`;
    }
}

// Drag and drop functionality
function initializeDragAndDrop() {
    document.querySelectorAll('.file-upload').forEach(uploadArea => {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            this.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            const input = this.querySelector('input[type="file"]');
            if (input) {
                input.files = e.dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        });
    });
}

// Form validation
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#dc3545';
            isValid = false;
        } else {
            field.style.borderColor = '#e1e5e9';
        }
    });
    
    return isValid;
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Export functions for global access
window.showTab = showTab;
window.updatePluginFormats = updatePluginFormats;
window.validateForm = validateForm;
window.showAlert = showAlert;
