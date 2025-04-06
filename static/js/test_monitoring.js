class TestMonitoring {
    constructor(attemptId) {
        this.attemptId = attemptId;
        console.log('TestMonitoring initialized with attempt ID:', this.attemptId);
        this.captureInterval = 30000; // 30 seconds between captures
        this.videoElement = null;
        this.canvasElement = null;
    }
    
    initialize() {
        // Create video and canvas elements
        this.createElements();
        
        // Request camera access
        this.requestCameraAccess();
        
        // Set up periodic captures
        this.setupPeriodicCaptures();
    }
    
    createElements() {
        // Create hidden video element
        this.videoElement = document.createElement('video');
        this.videoElement.style.display = 'none';
        this.videoElement.autoplay = true;
        document.body.appendChild(this.videoElement);
        
        // Create hidden canvas element
        this.canvasElement = document.createElement('canvas');
        this.canvasElement.style.display = 'none';
        document.body.appendChild(this.canvasElement);
    }
    
    requestCameraAccess() {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                this.videoElement.srcObject = stream;
                console.log('Camera access granted');
            })
            .catch(error => {
                console.error('Error accessing camera:', error);
            });
    }
    
    setupPeriodicCaptures() {
        // Take first capture after 5 seconds
        setTimeout(() => {
            this.captureImage();
        }, 5000);
        
        // Set up interval for subsequent captures
        setInterval(() => {
            this.captureImage();
        }, this.captureInterval);
    }
    
    captureImage() {
        if (!this.videoElement || !this.videoElement.srcObject) {
            console.error('Video element not ready');
            return;
        }
        
        // Set canvas dimensions to match video
        this.canvasElement.width = this.videoElement.videoWidth;
        this.canvasElement.height = this.videoElement.videoHeight;
        
        // Draw video frame to canvas
        const context = this.canvasElement.getContext('2d');
        context.drawImage(this.videoElement, 0, 0, this.canvasElement.width, this.canvasElement.height);
        
        // Convert canvas to blob
        this.canvasElement.toBlob(blob => {
            this.sendImageToServer(blob);
        }, 'image/jpeg', 0.8);
    }
    
    sendImageToServer(imageBlob) {
        // Debug the attempt ID
        console.log('Sending image with attempt ID:', this.attemptId);
        
        if (!this.attemptId) {
            console.error('Attempt ID is missing or empty');
            return;
        }
        
        const formData = new FormData();
        formData.append('image', imageBlob, 'capture.jpg');
        
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Use the correct URL format for your Django application
        const url = `/tests/attempt/${this.attemptId}/capture-image/`;
        console.log('Sending to URL:', url);
        
        fetch(url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Image capture response:', data);
        })
        .catch(error => {
            console.error('Error sending image to server:', error);
        });
    }
}