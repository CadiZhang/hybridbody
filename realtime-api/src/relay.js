import { WebSocketServer } from 'ws';
import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import FormData from 'form-data';
import fetch from 'node-fetch';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY environment variable is required');
}

const app = express();
app.use(cors());

// Add a test endpoint to check ESP32 camera connectivity
app.get('/test-esp32', async (req, res) => {
  try {
    const esp32Url = req.query.url || 'http://192.168.1.6:81/status';
    console.log(`Testing connection to ESP32 camera at ${esp32Url}`);
    
    // Add a timeout to the fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
    // Try to fetch the status page from the ESP32 camera
    const response = await fetch(esp32Url, { 
      signal: controller.signal,
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    }).finally(() => clearTimeout(timeoutId));
    
    // Get response data
    const data = await response.text();
    
    // Send connection details back to client
    res.json({
      success: true,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      dataLength: data.length,
      sampleData: data.substring(0, 100) + (data.length > 100 ? '...' : ''),
      url: esp32Url,
      timestamp: new Date().toISOString()
    });
    
    console.log(`Successfully connected to ESP32 camera at ${esp32Url}`);
  } catch (error) {
    console.error('Error connecting to ESP32 camera:', error);
    
    // Send a detailed error response
    res.status(500).json({ 
      success: false,
      error: error.message,
      code: error.code || 'UNKNOWN_ERROR',
      name: error.name,
      isAborted: error.name === 'AbortError',
      timestamp: new Date().toISOString(),
      url: req.query.url || 'http://192.168.1.6:81/status'
    });
  }
});

// Add a new endpoint to capture images from the ESP32 camera
app.get('/capture-image', async (req, res) => {
  try {
    const esp32Url = req.query.url || 'http://192.168.1.6:81/capture';
    console.log(`Capturing image from ESP32 camera at ${esp32Url}`);
    
    // Add a timeout to the fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    // Fetch image from the ESP32 camera
    const response = await fetch(esp32Url, { 
      signal: controller.signal,
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    }).finally(() => clearTimeout(timeoutId));
    
    if (!response.ok) {
      throw new Error(`Failed to fetch from ESP32: ${response.statusText} (${response.status})`);
    }
    
    // Get the image as a buffer
    const imageBuffer = await response.buffer();
    
    // Log image information
    console.log(`ESP32 Camera Image Details:
      - Size: ${imageBuffer.length} bytes
      - Content-Type: ${response.headers.get('content-type')}
      - Status: ${response.status}
    `);
    
    if (imageBuffer.length === 0) {
      throw new Error('Received empty image buffer from ESP32 camera');
    }
    
    // Set appropriate headers
    res.setHeader('Content-Type', 'image/jpeg');
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    // Send the image back to the client
    res.send(imageBuffer);
    
    console.log(`Successfully captured and sent image (${imageBuffer.length} bytes)`);
  } catch (error) {
    console.error('Error capturing image from ESP32 camera:', error);
    
    // Send a detailed error response
    res.status(500).json({ 
      error: error.message,
      code: error.code || 'UNKNOWN_ERROR',
      name: error.name,
      isAborted: error.name === 'AbortError',
      timestamp: new Date().toISOString()
    });
  }
});

const server = app.listen(8081, () => {
  console.log('Relay server running on http://localhost:8081');
});

const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  console.log('Client connected');

  ws.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      // Extract endpoint from message or default to chat/completions
      const endpoint = message.endpoint || '/v1/chat/completions';
      
      // Log complete message for debugging
      console.log(`Incoming WebSocket request for ${endpoint}:`, JSON.stringify({
        endpoint,
        hasModel: !!message.model,
        messageBodyKeys: Object.keys(message),
      }, null, 2));
      
      // Make a copy of the message without removing the endpoint property
      const messageBody = { ...message };
      // Only delete the endpoint property, keep everything else
      delete messageBody.endpoint;
      
      console.log(`Forwarding request to OpenAI endpoint: ${endpoint}`);
      
      // If model is missing for chat completions, add a default model
      if (endpoint === '/v1/chat/completions' && !messageBody.model) {
        messageBody.model = 'gpt-4o'; // Updated to use a current model that supports vision
        console.log('Added default model:', messageBody.model);
      }
      
      // Check if this is a fully-formed chat completion request or an internal real-time API event
      // Only add messages for vision requests (which come from take_picture)
      if (endpoint === '/v1/chat/completions' && !messageBody.messages && messageBody.type) {
        // This appears to be an internal event from the realtime API, not a chat completion request
        // Log the request but don't try to send it to OpenAI Chat API
        console.log('Skipping internal real-time API event:', messageBody.type);
        
        // Return a mock response
        ws.send(JSON.stringify({
          status: 200,
          data: { ok: true, event_handled: true }
        }));
        return;
      }
      
      // Determine content type and prepare request body
      let contentType = 'application/json';
      let body;
      let headers = {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      };
      
      // Handle multipart/form-data for image uploads
      if (message.isMultipart) {
        // Create a FormData object
        const formData = new FormData();
        
        // Add all fields to the form data
        Object.entries(messageBody).forEach(([key, value]) => {
          // Handle base64 encoded files
          if (key === 'file' || key === 'image' || key === 'mask') {
            if (typeof value === 'object' && value.data && value.mimetype) {
              // Convert base64 to buffer
              const buffer = Buffer.from(value.data, 'base64');
              formData.append(key, buffer, {
                filename: value.filename || 'file.png',
                contentType: value.mimetype
              });
            }
          } else if (Array.isArray(value)) {
            // Handle array values
            value.forEach(item => formData.append(key + '[]', item));
          } else {
            // Handle regular string/number values
            formData.append(key, value);
          }
        });
        
        // Use the form data as the body
        body = formData;
        // Use form data headers (including boundary)
        headers = {
          ...headers,
          ...formData.getHeaders()
        };
      } else {
        // Use JSON for regular requests
        contentType = 'application/json';
        headers['Content-Type'] = contentType;
        body = JSON.stringify(messageBody);
      }
      
      // Forward the message to OpenAI's API
      const apiUrl = `https://api.openai.com${endpoint}`;
      console.log(`Full API URL: ${apiUrl}`);
      console.log(`Request body:`, JSON.stringify(messageBody, null, 2));
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: headers,
        body: body
      });
      
      // Handle different response types
      let result;
      const contentTypeHeader = response.headers.get('content-type');
      
      if (contentTypeHeader && contentTypeHeader.includes('application/json')) {
        result = await response.json();
        // Log detailed error information for non-200 responses
        if (response.status !== 200) {
          console.error(`OpenAI API Error (${response.status}):`, JSON.stringify(result, null, 2));
        }
      } else {
        // Handle binary responses (like images or audio)
        const buffer = await response.arrayBuffer();
        result = {
          type: contentTypeHeader,
          data: Buffer.from(buffer).toString('base64'),
          status: response.status
        };
      }
      
      console.log(`Response received from OpenAI (status: ${response.status})`);
      ws.send(JSON.stringify({
        status: response.status,
        data: result
      }));
      
    } catch (error) {
      console.error('Error:', error);
      ws.send(JSON.stringify({ 
        error: error.message,
        status: 500
      }));
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
  });
}); 