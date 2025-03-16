/**
 * Fashion Recommendation System - Client-side functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const occasionSelect = document.getElementById('occasion');
    const customOccasionField = document.getElementById('custom-occasion-field');
    const traditionalFields = document.getElementById('traditional-fields');
    const fashionForm = document.getElementById('fashion-form');
// Remove duplicate declaration since it's already declared above
    
    // Image handling elements
    const fileInput = document.getElementById('image');
    const imagePreview = document.getElementById('image-preview');
    const cropperContainer = document.getElementById('cropper-container');
    const croppedImageContainer = document.getElementById('cropped-image-container');
    const croppedImage = document.getElementById('cropped-image');
    const croppedImageData = document.getElementById('cropped_image_data');
    const cropBtn = document.getElementById('crop-btn');
    const cancelCropBtn = document.getElementById('cancel-crop-btn');
    
    // Camera elements
    const startCameraBtn = document.getElementById('start-camera');
    const video = document.getElementById('video');
    const captureBtn = document.getElementById('capture');
    const retakeBtn = document.getElementById('retake');
    const cancelCameraBtn = document.getElementById('cancel-camera');
    const canvas = document.getElementById('canvas');
    const capturedImageInput = document.getElementById('captured_image');
    
    // Global variables
// Remove duplicate stream declaration since it's declared again later
// Remove this declaration since it's redeclared later in the code

    // Start Camera
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                video.style.display = 'block';
                captureBtn.style.display = 'block';
                cancelCameraBtn.style.display = 'block';
                startCameraBtn.style.display = 'none';
            } catch (err) {
                alert("Error accessing camera: " + err);
            }
        });
    }

    // Capture Image
    if (captureBtn) {
        captureBtn.addEventListener('click', () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const imageData = canvas.toDataURL('image/png');
            capturedImageInput.value = imageData;
            
            // Show canvas and retake button, hide video and capture button
            canvas.style.display = 'block';
            retakeBtn.style.display = 'block';
            video.style.display = 'none';
            captureBtn.style.display = 'none';
            
            // Keep cancel button visible
            cancelCameraBtn.style.display = 'block';
        });
    }

    // Retake Photo
    if (retakeBtn) {
        retakeBtn.addEventListener('click', () => {
            // Hide canvas and retake button
            canvas.style.display = 'none';
            retakeBtn.style.display = 'none';
            
            // Show video and capture button
            video.style.display = 'block';
            captureBtn.style.display = 'block';
            
            // Clear captured image
            capturedImageInput.value = '';
        });
    }

    // Cancel Camera
    if (cancelCameraBtn) {
        cancelCameraBtn.addEventListener('click', () => {
            // Stop camera stream
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Hide all camera elements
            video.style.display = 'none';
            canvas.style.display = 'none';
            captureBtn.style.display = 'none';
            retakeBtn.style.display = 'none';
            cancelCameraBtn.style.display = 'none';
            
            // Show start camera button
            startCameraBtn.style.display = 'block';
            
            // Clear captured image
            capturedImageInput.value = '';
        });
    }
    const skinToneSelect = document.getElementById('skin_tone');
    
    let cropper = null;
    let stream = null;

    // Handle occasion selection
    if (occasionSelect) {
        occasionSelect.addEventListener('change', function() {
            if (this.value === 'other') {
                customOccasionField.style.display = 'block';
            } else {
                customOccasionField.style.display = 'none';
            }
            
            if (this.value === 'traditional') {
                traditionalFields.style.display = 'block';
            } else {
                traditionalFields.style.display = 'none';
            }
        });
    }

    // Handle file input change with compression
    if (fileInput) {
        fileInput.addEventListener('change', async function(e) {
            if (e.target.files && e.target.files[0]) {
                const file = e.target.files[0];
                const maxSize = 5 * 1024 * 1024; // 5MB

                if (file.size > maxSize) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = new Image();
                        img.onload = function() {
                            const canvas = document.createElement('canvas');
                            let width = img.width;
                            let height = img.height;
                            
                            // Calculate new dimensions
                            if (width > height) {
                                if (width > 1920) {
                                    height *= 1920 / width;
                                    width = 1920;
                                }
                            } else {
                                if (height > 1920) {
                                    width *= 1920 / height;
                                    height = 1920;
                                }
                            }

                            canvas.width = width;
                            canvas.height = height;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0, width, height);
                            
                            // Compress and initialize cropper
                            const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.7);
                            initializeCropper(compressedDataUrl);
                        };
                        img.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                } else {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        initializeCropper(e.target.result);
                    };
                    reader.readAsDataURL(file);
                }
            }
        });
    }

    // Initialize cropper
    function initializeCropper(imageData) {
        imagePreview.src = imageData;
        cropperContainer.style.display = 'block';
        
        if (cropper) {
            cropper.destroy();
        }
        
        cropper = new Cropper(imagePreview, {
            aspectRatio: 1,
            viewMode: 1,
            guides: true,
            autoCropArea: 0.8,
            responsive: true
        });
    }

    // Handle crop button
    if (cropBtn) {
        cropBtn.addEventListener('click', function() {
            if (cropper) {
                const canvas = cropper.getCroppedCanvas({
                    width: 300,
                    height: 300
                });
                
                const croppedDataUrl = canvas.toDataURL('image/jpeg');
                croppedImage.src = croppedDataUrl;
                croppedImageContainer.style.display = 'block';
                croppedImageData.value = croppedDataUrl;
                cropperContainer.style.display = 'none';
                
                cropper.destroy();
                cropper = null;
            }
        });
    }

    // Handle cancel crop
    if (cancelCropBtn) {
        cancelCropBtn.addEventListener('click', function() {
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }
            cropperContainer.style.display = 'none';
            fileInput.value = '';
        });
    }

    // Form validation
    if (fashionForm) {
        fashionForm.addEventListener('submit', function(e) {
            if (skinToneSelect && skinToneSelect.value === 'unknown' && 
                (!fileInput.files.length && !capturedImageInput.value)) {
                e.preventDefault();
                alert('Please upload a photo for skin tone analysis or select your skin tone manually.');
                skinToneSelect.focus();
            }
        });
    }
});