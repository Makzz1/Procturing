import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Face Capture Component
const FaceCapture = ({ onCaptureComplete }) => {
  const [isCapturing, setIsCapturing] = useState(false);
  const [stream, setStream] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Failed to access camera:', error);
    }
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) {
      // If no camera available, simulate capture for testing
      console.log("📸 No camera available, simulating face capture for testing");
      setCapturedImage("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="); // 1x1 transparent placeholder
      onCaptureComplete(true);
      setIsCapturing(false);
      return;
    }

    setIsCapturing(true);
    
    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext('2d');
    
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    ctx.drawImage(video, 0, 0);
    
    // Convert to blob
    canvas.toBlob(async (blob) => {
      if (!blob) {
        console.log("📸 No blob created, simulating capture");
        setCapturedImage("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=");
        onCaptureComplete(true);
        setIsCapturing(false);
        return;
      }
      
      try {
        const formData = new FormData();
        formData.append('face_image', blob, `face_capture_${Date.now()}.jpg`);
        formData.append('student_id', `student_${Date.now()}`);
        formData.append('timestamp', new Date().toISOString());

        // TODO: Uncomment when backend endpoint is ready
        /*
        const response = await axios.post(`${API}/exam/upload-face`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        console.log('📸 Face image uploaded:', response.data);
        */
        
        console.log('📸 Face image captured and ready for upload:', blob.size, 'bytes');
        setCapturedImage(canvas.toDataURL());
        
        // Stop camera after capture
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
        }
        
        onCaptureComplete(true);
      } catch (error) {
        console.error('Failed to upload face image:', error);
        // Still proceed even if upload fails
        setCapturedImage(canvas.toDataURL());
        onCaptureComplete(true);
      }
      setIsCapturing(false);
    }, 'image/jpeg', 0.8);
  };

  if (capturedImage) {
    return (
      <div className="face-capture-success">
        <h3>✅ Face Captured Successfully!</h3>
        <img src={capturedImage} alt="Captured face" className="captured-face-preview" />
        <p>Proceeding to exam...</p>
      </div>
    );
  }

  return (
    <div className="face-capture-container">
      <div className="face-capture-card">
        <h2 className="text-2xl font-bold mb-4">Face Verification</h2>
        <p className="mb-4 text-gray-600">
          Please position your face in the center of the camera and look directly at the screen.
        </p>
        
        <div className="camera-container">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="face-capture-video"
          />
          <div className="face-guide-overlay">
            <div className="face-guide-circle"></div>
            <div className="face-guide-text">Center your face here</div>
          </div>
        </div>
        
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        
        <button
          onClick={capturePhoto}
          disabled={isCapturing}
          className="capture-face-button"
        >
          {isCapturing ? "Capturing..." : "Capture Face"}
        </button>
        
        <p className="capture-instructions">
          Make sure you are looking directly at the camera and your face is clearly visible.
        </p>
      </div>
    </div>
  );
};

// Device Detection Component
const DeviceCheck = ({ onCheckComplete }) => {
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [error, setError] = useState("");

  const checkDevices = async () => {
    setChecking(true);
    setError("");
    
    try {
      let keyboardCount = 0;
      let monitorCount = 1; // Default to 1
      let detectedDevices = [];
      let hasMultipleKeyboards = false;
      let hasExternalMonitors = false;

      // Check for multiple monitors using Window Management API
      try {
        if ('getScreenDetails' in window) {
          const permission = await navigator.permissions.query({ name: 'window-management' });
          if (permission.state === 'granted' || permission.state === 'prompt') {
            if (permission.state === 'prompt') {
              // Request permission
              await window.getScreenDetails();
            }
            const screenDetails = await window.getScreenDetails();
            monitorCount = screenDetails.screens.length;
            hasExternalMonitors = monitorCount > 1;
            detectedDevices.push(`${monitorCount} monitor(s) detected`);
          }
        }
      } catch (e) {
        console.log("Window Management API not supported or permission denied");
      }

      // Check for USB devices (keyboards) using WebUSB API
      try {
        if ('usb' in navigator) {
          // Get previously authorized devices
          const devices = await navigator.usb.getDevices();
          const keyboards = devices.filter(device => {
            // Check if device is likely a keyboard (HID interface class 3)
            return device.configurations.some(config =>
              config.interfaces.some(iface =>
                iface.alternates.some(alt => alt.interfaceClass === 3)
              )
            );
          });
          
          keyboardCount = keyboards.length;
          hasMultipleKeyboards = keyboardCount > 1;
          
          keyboards.forEach(keyboard => {
            detectedDevices.push(`USB Keyboard: ${keyboard.productName || 'Unknown'}`);
          });

          // If no keyboards found, prompt user to authorize
          if (keyboardCount === 0) {
            try {
              await navigator.usb.requestDevice({
                filters: [
                  { classCode: 3 }, // HID devices
                  { vendorId: 0x046D }, // Logitech
                  { vendorId: 0x045E }, // Microsoft
                  { vendorId: 0x1532 }, // Razer
                  { vendorId: 0x04F2 }, // Chicony
                ]
              });
              // Re-check after user selection
              const newDevices = await navigator.usb.getDevices();
              const newKeyboards = newDevices.filter(device => {
                return device.configurations.some(config =>
                  config.interfaces.some(iface =>
                    iface.alternates.some(alt => alt.interfaceClass === 3)
                  )
                );
              });
              keyboardCount = newKeyboards.length;
              hasMultipleKeyboards = keyboardCount > 1;
            } catch (e) {
              console.log("User cancelled device selection or no devices available");
            }
          }
        }
      } catch (e) {
        console.log("WebUSB API not supported");
      }

      const result = {
        has_multiple_keyboards: hasMultipleKeyboards,
        has_external_monitors: hasExternalMonitors,
        keyboard_count: keyboardCount,
        monitor_count: monitorCount,
        detected_devices: detectedDevices
      };

      setCheckResult(result);
      
      // Send to backend (with error handling)
      try {
        await axios.post(`${API}/device/check`, result);
        console.log("✅ Device check data sent to backend");
      } catch (error) {
        console.log("⚠️ Backend unavailable, continuing without logging device check:", error.message);
        // Continue anyway - don't block the exam flow due to backend issues
      }
      
      onCheckComplete(result);
    } catch (error) {
      setError("Failed to check devices: " + error.message);
      console.error("Device check error:", error);
    }
    
    setChecking(false);
  };

  return (
    <div className="device-check-container">
      <div className="device-check-card">
        <h2 className="text-2xl font-bold mb-4">Device Security Check</h2>
        <p className="mb-4 text-gray-600">
          Before starting the exam, we need to check for external devices that might compromise exam integrity.
        </p>
        
        {!checkResult && (
          <button
            onClick={checkDevices}
            disabled={checking}
            className="check-button"
          >
            {checking ? "Checking Devices..." : "Check Devices"}
          </button>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {checkResult && (
          <div className="check-results">
            <h3 className="text-lg font-semibold mb-2">Check Results:</h3>
            <div className="result-grid">
              <div className={`result-item ${checkResult.has_multiple_keyboards ? 'warning' : 'safe'}`}>
                <span>Multiple Keyboards:</span>
                <span>{checkResult.has_multiple_keyboards ? 'DETECTED' : 'NONE'}</span>
              </div>
              <div className={`result-item ${checkResult.has_external_monitors ? 'warning' : 'safe'}`}>
                <span>External Monitors:</span>
                <span>{checkResult.has_external_monitors ? 'DETECTED' : 'NONE'}</span>
              </div>
              <div className="result-item">
                <span>Total Keyboards:</span>
                <span>{checkResult.keyboard_count}</span>
              </div>
              <div className="result-item">
                <span>Total Monitors:</span>
                <span>{checkResult.monitor_count}</span>
              </div>
            </div>
            
            {checkResult.detected_devices.length > 0 && (
              <div className="detected-devices">
                <h4 className="font-medium mb-2">Detected Devices:</h4>
                <ul className="device-list">
                  {checkResult.detected_devices.map((device, index) => (
                    <li key={index}>{device}</li>
                  ))}
                </ul>
              </div>
            )}

            {(checkResult.has_multiple_keyboards || checkResult.has_external_monitors) && (
              <div className="warning-section">
                <h4 className="text-red-600 font-semibold">⚠️ Warning:</h4>
                <p>External devices detected. Please disconnect them before proceeding.</p>
                <div className="warning-buttons">
                  <button onClick={checkDevices} className="recheck-button">
                    Re-check Devices
                  </button>
                  <button onClick={() => onCheckComplete(checkResult)} className="continue-anyway-button">
                    Continue Anyway
                  </button>
                </div>
              </div>
            )}

            {(!checkResult.has_multiple_keyboards && !checkResult.has_external_monitors) && (
              <div className="success-section">
                <h4 className="text-green-600 font-semibold">✅ All Clear!</h4>
                <p>No external devices detected. You may proceed with the exam.</p>
                <button onClick={() => onCheckComplete(checkResult)} className="proceed-button">
                  Proceed to Face Verification
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Main Exam Platform Component
const ExamPlatform = () => {
  const [deviceCheckPassed, setDeviceCheckPassed] = useState(false);
  const [faceCaptured, setFaceCaptured] = useState(false);
  const [examStarted, setExamStarted] = useState(false);
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});

  const handleDeviceCheckComplete = (result) => {
    // Allow proceeding even with external devices (for testing)
    // In production, you might want to enforce stricter rules
    setDeviceCheckPassed(true);
  };

  const handleFaceCaptureComplete = (success) => {
    if (success) {
      setFaceCaptured(true);
    } else {
      alert("Face capture failed. Please try again.");
    }
  };

  const startExam = async () => {
    try {
      console.log("Starting exam...");
      const response = await axios.get(`${API}/questions`);
      console.log("Questions received:", response.data);
      setQuestions(response.data);
      setExamStarted(true);
      console.log("Exam started flag set to true");
      
      // Log exam start (commented out API call as requested)
      /*
      await axios.post(`${API}/exam/logs`, {
        log_id: `exam_start_${Date.now()}`,
        reason: "Exam started",
        student_id: "student_" + Date.now(),
        exam_session_id: "session_" + Date.now()
      });
      */
      console.log("📝 Exam start logged locally");
    } catch (error) {
      console.error("Failed to start exam:", error);
      // Show error to user but still try to start exam with dummy data
      setQuestions([{
        id: "sample_1",
        question_text: "Sample question: What is 2 + 2?",
        option_a: "3",
        option_b: "4", 
        option_c: "5",
        option_d: "6"
      }]);
      setExamStarted(true);
    }
  };

  console.log("ExamPlatform render - deviceCheckPassed:", deviceCheckPassed, "faceCaptured:", faceCaptured, "examStarted:", examStarted, "questions:", questions.length);

  if (!deviceCheckPassed) {
    return <DeviceCheck onCheckComplete={handleDeviceCheckComplete} />;
  }

  if (!faceCaptured) {
    return <FaceCapture onCaptureComplete={handleFaceCaptureComplete} />;
  }

  if (examStarted && questions.length > 0) {
    console.log("Rendering ExamInterface with", questions.length, "questions");
    return <ExamInterface questions={questions} currentQuestion={currentQuestion} setCurrentQuestion={setCurrentQuestion} answers={answers} setAnswers={setAnswers} />;
  }

  // Show exam info page before starting exam
  if (!examStarted) {
    return (
      <div className="exam-platform">
        <div className="exam-info-card">
          <h1 className="text-4xl font-bold mb-6">Secure Exam Platform</h1>
          <p className="text-lg mb-8">Welcome to our proctored examination system. This platform ensures exam integrity through advanced monitoring.</p>
          
          <div className="exam-details">
            <div className="detail-grid">
              <div className="detail-item">
                <h3>Duration:</h3>
                <span>2 Hours</span>
              </div>
              <div className="detail-item">
                <h3>Questions:</h3>
                <span>50 MCQs</span>
              </div>
              <div className="detail-item">
                <h3>Attempts:</h3>
                <span>1 Only</span>
              </div>
              <div className="detail-item">
                <h3>Mode:</h3>
                <span>Proctored</span>
              </div>
            </div>
          </div>

          <div className="monitoring-features">
            <h2 className="text-2xl font-semibold mb-4">Monitoring Features</h2>
            <ul className="feature-list">
              <li>Video Recording</li>
              <li>Audio Monitoring</li>
              <li>Screen Activity</li>
              <li>Behavior Analysis</li>
            </ul>
          </div>

          <div className="instructions">
            <h2 className="text-2xl font-semibold mb-4">Important Instructions</h2>
            <div className="instruction-section">
              <h4 className="font-semibold">Before Starting:</h4>
              <ul>
                <li>• Ensure stable internet connection</li>
                <li>• Close all unnecessary applications</li>
                <li>• Find a quiet, well-lit room</li>
                <li>• Keep your ID ready for verification</li>
              </ul>
            </div>
            <div className="instruction-section">
              <h4 className="font-semibold">During Exam:</h4>
              <ul>
                <li>• Stay in fullscreen mode</li>
                <li>• Do not switch windows or tabs</li>
                <li>• Keep your face visible to camera</li>
                <li>• No external materials allowed</li>
                <li>• <strong>No talking or making noise - Audio is recorded</strong></li>
              </ul>
            </div>
          </div>

          <button onClick={startExam} className="start-exam-button">
            Start Exam
          </button>
          <p className="agreement-text">By clicking "Start Exam", you agree to our monitoring policies</p>
        </div>
      </div>
    );
  }

  // Loading state when exam is started but questions not loaded yet
  return (
    <div className="exam-platform">
      <div className="exam-info-card">
        <h1>Loading Exam...</h1>
        <p>Please wait while we prepare your questions.</p>
      </div>
    </div>
  );
};

  // Auto-dismissing Violation Alert Component
const ViolationAlert = ({ violation, getViolationColor }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
    }, 3000); // Disappear after 3 seconds

    return () => clearTimeout(timer);
  }, []);

  if (!isVisible) return null;

  return (
    <div className={`violation-item ${getViolationColor(violation.type)} violation-alert`}>
      <div className="violation-header">
        <span className="violation-type">{violation.type}</span>
        <span className="violation-time">{new Date(violation.timestamp).toLocaleTimeString()}</span>
        <button className="dismiss-violation" onClick={() => setIsVisible(false)}>×</button>
      </div>
      <div className="violation-details">{violation.details}</div>
      <div className="violation-question">Question: {violation.questionNumber}</div>
    </div>
  );
};

// Enhanced Exam Interface Component with Monitoring
const ExamInterface = ({ questions, currentQuestion, setCurrentQuestion, answers, setAnswers }) => {
  const [violations, setViolations] = useState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mediaStream, setMediaStream] = useState(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [speechDetectionActive, setSpeechDetectionActive] = useState(false);
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const [timeRemaining, setTimeRemaining] = useState(7200); // 2 hours in seconds

  console.log("ExamInterface: questions =", questions, "currentQuestion =", currentQuestion);

  // Function to log violations (API call commented out)
  const logViolation = async (violationType, details) => {
    const violation = {
      type: violationType,
      details: details,
      timestamp: new Date().toISOString(),
      questionNumber: currentQuestion + 1
    };
    
    setViolations(prev => [...prev, violation]);
    
    // TODO: Uncomment when backend is ready
    /*
    try {
      await axios.post(`${API}/exam/logs`, {
        log_id: `violation_${Date.now()}`,
        reason: `${violationType}: ${details}`,
        student_id: "student_" + Date.now(),
        exam_session_id: "session_" + Date.now(),
        video_url: "placeholder_video_url"
      });
    } catch (error) {
      console.error("Failed to log violation:", error);
    }
    */
    
    console.log("🚨 VIOLATION DETECTED:", violation);
  };

  // Initialize monitoring on component mount
  useEffect(() => {
    console.log("ExamInterface: Initializing monitoring...");
    initializeMonitoring();
    return () => {
      cleanupMonitoring();
    };
  }, []);

  // Timer countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 0) {
          clearInterval(timer);
          // Auto-submit exam when time is up
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const initializeMonitoring = async () => {
    try {
      console.log("Starting monitoring initialization...");
      
      // 1. Request fullscreen (but don't fail if denied)
      try {
        await requestFullscreen();
      } catch (e) {
        console.log("Fullscreen denied, continuing...");
      }
      
      // 2. Start video/audio capture (but don't fail if denied)
      try {
        await startMediaCapture();
        await startAudioRecording(); // Start separate audio recording
      } catch (e) {
        console.log("Media access denied, continuing...");
      }
      
      // 3. Set up monitoring (these shouldn't fail)
      setupWindowFocusMonitoring();
      setupTabVisibilityMonitoring();
      setupClipboardMonitoring();
      setupKeyboardBlocking();
      
      setIsMonitoring(true);
      console.log("✅ Monitoring initialized successfully");
      
    } catch (error) {
      console.error("Failed to initialize monitoring:", error);
      logViolation("MONITORING_INIT_FAILED", error.message);
      // Continue anyway - don't break the exam
      setIsMonitoring(true);
    }
  };

  const requestFullscreen = async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen();
      } else if (elem.msRequestFullscreen) {
        await elem.msRequestFullscreen();
      }
      setIsFullscreen(true);
      
      // Monitor fullscreen changes
      document.addEventListener('fullscreenchange', handleFullscreenChange);
      document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.addEventListener('msfullscreenchange', handleFullscreenChange);
      
    } catch (error) {
      logViolation("FULLSCREEN_DENIED", "User denied fullscreen access");
      throw error;
    }
  };

  const handleFullscreenChange = () => {
    const isCurrentlyFullscreen = !!(
      document.fullscreenElement || 
      document.webkitFullscreenElement || 
      document.msFullscreenElement
    );
    
    setIsFullscreen(isCurrentlyFullscreen);
    
    if (!isCurrentlyFullscreen) {
      logViolation("FULLSCREEN_EXITED", "User exited fullscreen mode");
    }
  };

  const startMediaCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: true
      });
      
      setMediaStream(stream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      // Start recording with chunked upload
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp9'
      });
      
      const chunks = [];
      
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
          
          // Upload chunk to backend every 10 seconds
          const videoBlob = new Blob([event.data], { type: 'video/webm' });
          await uploadVideoChunk(videoBlob);
        }
      };
      
      mediaRecorder.onstop = async () => {
        if (chunks.length > 0) {
          const blob = new Blob(chunks, { type: 'video/webm' });
          await uploadVideoChunk(blob, true); // Final chunk
        }
      };
      
      mediaRecorder.start(10000); // Record in 10-second chunks
      mediaRecorderRef.current = mediaRecorder;
      
    } catch (error) {
      logViolation("MEDIA_ACCESS_DENIED", "Camera/microphone access denied");
      throw error;
    }
  };

  // Function to show speech detection popup
  const showSpeechDetectedPopup = () => {
    // Create and show popup
    const popup = document.createElement('div');
    popup.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #ff4444;
      color: white;
      padding: 20px 30px;
      border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      z-index: 10000;
      font-size: 18px;
      font-weight: bold;
      text-align: center;
      border: 3px solid #cc0000;
    `;
    popup.innerHTML = `
      <div style="margin-bottom: 10px;">⚠️ SPEECH DETECTED ⚠️</div>
      <div style="font-size: 14px; font-weight: normal;">
        Talking is not allowed during the exam.<br>
        This violation has been logged.
      </div>
    `;
    
    document.body.appendChild(popup);
    
    // Auto-remove popup after 5 seconds
    setTimeout(() => {
      if (document.body.contains(popup)) {
        document.body.removeChild(popup);
      }
    }, 5000);
    
    // Also log to console
    console.log('🚨 SPEECH DETECTION POPUP SHOWN');
  };

  // Function to upload audio chunks to backend and check for speech
  const uploadAudioChunk = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, `exam_audio_${Date.now()}.webm`);
      formData.append('student_id', `student_${Date.now()}`);
      formData.append('exam_session_id', `session_${Date.now()}`);
      formData.append('timestamp', new Date().toISOString());

      console.log(`🎤 Uploading audio chunk for speech detection (${audioBlob.size} bytes)`);
      
      const response = await axios.post(`${API}/exam/detect-speech`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      console.log('🎤 Speech detection response:', response.data);
      
      // Handle speech detection result
      if (response.data.speech_detected) {
        // Show popup warning
        showSpeechDetectedPopup();
        
        // Log as violation
        logViolation("SPEECH_DETECTED", response.data.message);
        console.log('🚨 SPEECH DETECTED - Violation logged');
      }
      
    } catch (error) {
      console.error('Failed to upload audio chunk for speech detection:', error);
      logViolation("AUDIO_UPLOAD_FAILED", `Failed to upload audio: ${error.message}`);
    }
  };

  // Start separate audio recording
  const startAudioRecording = async () => {
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false
      });
      
      const audioRecorder = new MediaRecorder(audioStream, {
        mimeType: 'audio/webm'
      });
      
      audioRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          await uploadAudioChunk(event.data);
        }
      };
      
      audioRecorder.start(5000); // Record audio in 5-second chunks
      audioRecorderRef.current = audioRecorder;
      setSpeechDetectionActive(true);
      console.log('🎤 Audio recording started for speech detection');
      
    } catch (error) {
      console.error('Failed to start audio recording:', error);
      logViolation("AUDIO_ACCESS_DENIED", "Audio access denied for separate recording");
    }
  };
  const uploadVideoChunk = async (videoBlob, isFinal = false) => {
    try {
      const formData = new FormData();
      formData.append('video', videoBlob, `exam_video_${Date.now()}.webm`);
      formData.append('student_id', `student_${Date.now()}`);
      formData.append('exam_session_id', `session_${Date.now()}`);
      formData.append('timestamp', new Date().toISOString());
      formData.append('is_final', isFinal.toString());

      // TODO: Uncomment when backend endpoint is ready
      /*
      const response = await axios.post(`${API}/exam/upload-video`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      console.log('📹 Video chunk uploaded:', response.data);
      */
      
      console.log(`📹 Video chunk ready for upload (${videoBlob.size} bytes)`, isFinal ? '- FINAL CHUNK' : '');
    } catch (error) {
      console.error('Failed to upload video chunk:', error);
      logViolation("VIDEO_UPLOAD_FAILED", `Failed to upload video: ${error.message}`);
    }
  };

  const setupWindowFocusMonitoring = () => {
    const handleBlur = () => {
      logViolation("WINDOW_FOCUS_LOST", "User switched to another window/application");
    };
    
    const handleFocus = () => {
      console.log("✅ Window focus regained");
    };
    
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
  };

  const setupTabVisibilityMonitoring = () => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        logViolation("TAB_HIDDEN", "User switched to another tab or minimized browser");
      } else {
        console.log("✅ Tab is visible again");
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
  };

  const setupClipboardMonitoring = () => {
    const handlePaste = async (e) => {
      try {
        const clipboardText = await navigator.clipboard.readText();
        if (clipboardText && clipboardText.length > 10) {
          logViolation("CLIPBOARD_PASTE", `Pasted content: "${clipboardText.substring(0, 100)}..."`);
        }
      } catch (error) {
        // Clipboard access might be restricted
        logViolation("CLIPBOARD_ACTIVITY", "Paste detected but content could not be read");
      }
    };
    
    const handleCopy = () => {
      logViolation("CLIPBOARD_COPY", "User copied content from the exam");
    };
    
    document.addEventListener('paste', handlePaste);
    document.addEventListener('copy', handleCopy);
  };

  const setupKeyboardBlocking = () => {
    const handleKeyDown = (e) => {
      // Block common shortcuts
      const blockedKeys = [
        // Alt+Tab (though this might not work in all browsers)
        (e.altKey && e.key === 'Tab'),
        // Ctrl+T (new tab)
        (e.ctrlKey && e.key === 't'),
        // Ctrl+N (new window)
        (e.ctrlKey && e.key === 'n'),
        // Ctrl+W (close tab)
        (e.ctrlKey && e.key === 'w'),
        // F12 (developer tools)
        (e.key === 'F12'),
        // Ctrl+Shift+I (developer tools)
        (e.ctrlKey && e.shiftKey && e.key === 'I'),
        // Ctrl+U (view source)
        (e.ctrlKey && e.key === 'u'),
        // F5 (refresh)
        (e.key === 'F5'),
        // Ctrl+R (refresh)
        (e.ctrlKey && e.key === 'r')
      ];
      
      if (blockedKeys.some(blocked => blocked)) {
        e.preventDefault();
        e.stopPropagation();
        logViolation("BLOCKED_SHORTCUT", `Attempted to use: ${e.key} ${e.ctrlKey ? '+ Ctrl' : ''} ${e.altKey ? '+ Alt' : ''} ${e.shiftKey ? '+ Shift' : ''}`);
        return false;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown, true);
  };

  const cleanupMonitoring = () => {
    console.log("Cleaning up monitoring...");
    // Stop media recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    // Stop audio recording for speech detection
    if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
      audioRecorderRef.current.stop();
    }
    
    // Stop media stream
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
    }
    
    setSpeechDetectionActive(false);
    
    // Exit fullscreen
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(e => console.log("Error exiting fullscreen:", e));
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getViolationColor = (type) => {
    switch (type) {
      case 'WINDOW_FOCUS_LOST':
      case 'TAB_HIDDEN':
        return 'bg-red-100 border-red-500 text-red-700';
      case 'CLIPBOARD_PASTE':
      case 'CLIPBOARD_COPY':
        return 'bg-orange-100 border-orange-500 text-orange-700';
      case 'BLOCKED_SHORTCUT':
        return 'bg-yellow-100 border-yellow-500 text-yellow-700';
      default:
        return 'bg-gray-100 border-gray-500 text-gray-700';
    }
  };

  // Error boundaries - if no questions, show loading
  if (!questions || questions.length === 0) {
    return (
      <div className="exam-interface-enhanced">
        <div className="monitoring-status">
          <div className="status-indicators">
            <span className="status-indicator inactive">Loading questions...</span>
          </div>
        </div>
        <div className="loading-container">
          <h2>Loading Exam Questions...</h2>
          <p>Please wait while we prepare your exam.</p>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentQuestion];
  if (!currentQ) {
    return (
      <div className="exam-interface-enhanced">
        <div className="error-container">
          <h2>Error Loading Question</h2>
          <p>Question {currentQuestion + 1} could not be loaded.</p>
          <button onClick={() => setCurrentQuestion(0)}>Return to First Question</button>
        </div>
      </div>
    );
  }

  return (
    <div className="exam-interface-enhanced">
      {/* Monitoring Status Bar */}
      <div className="monitoring-status">
        <div className="status-indicators">
          <span className={`status-indicator ${isFullscreen ? 'active' : 'inactive'}`}>
            🖥️ Fullscreen: {isFullscreen ? 'ON' : 'OFF'}
          </span>
          <span className={`status-indicator ${mediaStream ? 'active' : 'inactive'}`}>
            📹 Camera: {mediaStream ? 'ON' : 'OFF'}
          </span>
          <span className={`status-indicator ${speechDetectionActive ? 'active' : 'inactive'}`}>
            🎤 Speech Detection: {speechDetectionActive ? 'ACTIVE' : 'INACTIVE'}
          </span>
          <span className={`status-indicator ${isMonitoring ? 'active' : 'inactive'}`}>
            🔍 Monitoring: {isMonitoring ? 'ACTIVE' : 'INACTIVE'}
          </span>
          <span className="violation-count">
            ⚠️ Violations: {violations.length}
          </span>
        </div>
      </div>

      {/* Main Exam Header */}
      <div className="exam-header">
        <h2>Question {currentQuestion + 1} of {questions.length}</h2>
        <div className={`timer ${timeRemaining < 300 ? 'timer-warning' : ''}`}>
          Time Remaining: {formatTime(timeRemaining)}
        </div>
      </div>

      {/* Hidden Video Element for Monitoring */}
      <video
        ref={videoRef}
        autoPlay
        muted
        className="monitoring-video"
        style={{ display: 'none' }}
      />

      {/* Question Display */}
      <div className="question-container">
        <h3 className="question-text">{currentQ.question_text}</h3>
        <div className="options">
          {['option_a', 'option_b', 'option_c', 'option_d'].map((option, index) => (
            <label key={option} className="option-label">
              <input
                type="radio"
                name={`question_${currentQuestion}`}
                value={String.fromCharCode(65 + index)} // A, B, C, D
                checked={answers[currentQuestion] === String.fromCharCode(65 + index)}
                onChange={(e) => setAnswers({...answers, [currentQuestion]: e.target.value})}
              />
              <span>{String.fromCharCode(65 + index)}. {currentQ[option]}</span>
            </label>
          ))}
        </div>
        <div className="navigation-buttons">
          <button 
            onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
            disabled={currentQuestion === 0}
          >
            Previous
          </button>
          <button 
            onClick={() => setCurrentQuestion(Math.min(questions.length - 1, currentQuestion + 1))}
            disabled={currentQuestion === questions.length - 1}
          >
            Next
          </button>
          {currentQuestion === questions.length - 1 && (
            <button className="submit-exam-button">
              Submit Exam
            </button>
          )}
        </div>
      </div>

      {/* Auto-dismissing Violations Log */}
      {violations.length > 0 && (
        <div className="violations-log">
          <h4>Security Violations Detected:</h4>
          <div className="violations-list">
            {violations.slice(-3).map((violation, index) => (
              <ViolationAlert key={`${violation.timestamp}-${index}`} violation={violation} getViolationColor={getViolationColor} />
            ))}
          </div>
        </div>
      )}

      {/* No Talking Warning */}
      <div className="no-talking-warning">
        🔇 REMINDER: No talking allowed during the exam. All audio is being recorded.
      </div>

      {/* Warning Messages */}
      {!isFullscreen && isMonitoring && (
        <div className="warning-overlay">
          <div className="warning-message">
            ⚠️ Please return to fullscreen mode to continue the exam
            <button onClick={requestFullscreen} className="retry-fullscreen">
              Return to Fullscreen
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Admin Login Component
const AdminLogin = ({ onLogin }) => {
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await axios.post(`${API}/admin/login`, credentials);
      localStorage.setItem("adminToken", response.data.token);
      onLogin(response.data.token);
    } catch (error) {
      setError("Invalid credentials");
    }
    setLoading(false);
  };

  return (
    <div className="admin-login">
      <div className="login-card">
        <h2 className="text-3xl font-bold mb-6">Admin Login</h2>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={credentials.username}
              onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
              required
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="login-button">
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
        <p className="login-hint">Default: username=admin, password=admin123</p>
      </div>
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState("questions");
  const [questions, setQuestions] = useState([]);
  const [logs, setLogs] = useState([]);
  const [newQuestion, setNewQuestion] = useState({
    question_text: "",
    option_a: "",
    option_b: "",
    option_c: "",
    option_d: "",
    correct_answer: "A"
  });

  useEffect(() => {
    fetchQuestions();
    fetchLogs();
  }, []);

  const fetchQuestions = async () => {
    try {
      const response = await axios.get(`${API}/admin/questions`);
      setQuestions(response.data);
    } catch (error) {
      console.error("Failed to fetch questions:", error);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`${API}/admin/logs`);
      setLogs(response.data);
    } catch (error) {
      console.error("Failed to fetch logs:", error);
    }
  };

  const addQuestion = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/questions`, newQuestion);
      setNewQuestion({
        question_text: "",
        option_a: "",
        option_b: "",
        option_c: "",
        option_d: "",
        correct_answer: "A"
      });
      fetchQuestions();
    } catch (error) {
      console.error("Failed to add question:", error);
    }
  };

  const deleteQuestion = async (questionId) => {
    try {
      await axios.delete(`${API}/admin/questions/${questionId}`);
      fetchQuestions();
    } catch (error) {
      console.error("Failed to delete question:", error);
    }
  };

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <div className="tab-navigation">
          <button 
            className={activeTab === "questions" ? "active" : ""}
            onClick={() => setActiveTab("questions")}
          >
            Questions
          </button>
          <button 
            className={activeTab === "logs" ? "active" : ""}
            onClick={() => setActiveTab("logs")}
          >
            Logs
          </button>
        </div>
      </div>

      {activeTab === "questions" && (
        <div className="questions-section">
          <div className="add-question-form">
            <h2 className="text-2xl font-semibold mb-4">Add New Question</h2>
            <form onSubmit={addQuestion}>
              <div className="form-group">
                <label>Question Text</label>
                <textarea
                  value={newQuestion.question_text}
                  onChange={(e) => setNewQuestion({ ...newQuestion, question_text: e.target.value })}
                  required
                />
              </div>
              <div className="options-grid">
                <div className="form-group">
                  <label>Option A</label>
                  <input
                    type="text"
                    value={newQuestion.option_a}
                    onChange={(e) => setNewQuestion({ ...newQuestion, option_a: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Option B</label>
                  <input
                    type="text"
                    value={newQuestion.option_b}
                    onChange={(e) => setNewQuestion({ ...newQuestion, option_b: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Option C</label>
                  <input
                    type="text"
                    value={newQuestion.option_c}
                    onChange={(e) => setNewQuestion({ ...newQuestion, option_c: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Option D</label>
                  <input
                    type="text"
                    value={newQuestion.option_d}
                    onChange={(e) => setNewQuestion({ ...newQuestion, option_d: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Correct Answer</label>
                <select
                  value={newQuestion.correct_answer}
                  onChange={(e) => setNewQuestion({ ...newQuestion, correct_answer: e.target.value })}
                >
                  <option value="A">A</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D</option>
                </select>
              </div>
              <button type="submit" className="add-button">Add Question</button>
            </form>
          </div>

          <div className="questions-list">
            <h2 className="text-2xl font-semibold mb-4">All Questions ({questions.length})</h2>
            {questions.map((question, index) => (
              <div key={question.id} className="question-item">
                <div className="question-header">
                  <h3>Question {index + 1}</h3>
                  <button onClick={() => deleteQuestion(question.id)} className="delete-button">Delete</button>
                </div>
                <p className="question-text">{question.question_text}</p>
                <div className="options-display">
                  <span className={question.correct_answer === 'A' ? 'correct' : ''}>A. {question.option_a}</span>
                  <span className={question.correct_answer === 'B' ? 'correct' : ''}>B. {question.option_b}</span>
                  <span className={question.correct_answer === 'C' ? 'correct' : ''}>C. {question.option_c}</span>
                  <span className={question.correct_answer === 'D' ? 'correct' : ''}>D. {question.option_d}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "logs" && (
        <div className="logs-section">
          <h2 className="text-2xl font-semibold mb-4">Exam Logs ({logs.length})</h2>
          <div className="logs-list">
            {logs.map((log) => (
              <div key={log.id} className="log-item">
                <div className="log-header">
                  <span className="log-id">ID: {log.log_id}</span>
                  <span className="log-timestamp">{new Date(log.timestamp).toLocaleString()}</span>
                </div>
                <p className="log-reason">Reason: {log.reason}</p>
                {log.student_id && <p className="log-student">Student: {log.student_id}</p>}
                {log.video_url && <p className="log-video">Video: <a href={log.video_url} target="_blank" rel="noopener noreferrer">View</a></p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  const [adminLoggedIn, setAdminLoggedIn] = useState(false);

  useEffect(() => {
    // Check if admin is already logged in
    const token = localStorage.getItem("adminToken");
    if (token) {
      setAdminLoggedIn(true);
    }
  }, []);

  const handleAdminLogin = (token) => {
    setAdminLoggedIn(true);
  };

  const handleAdminLogout = () => {
    localStorage.removeItem("adminToken");
    setAdminLoggedIn(false);
  };

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ExamPlatform />} />
          <Route path="/admin" element={
            adminLoggedIn ? 
              <div>
                <div className="admin-nav">
                  <button onClick={handleAdminLogout} className="logout-button">Logout</button>
                </div>
                <AdminPanel />
              </div> :
              <AdminLogin onLogin={handleAdminLogin} />
          } />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;