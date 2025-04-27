import WebSocket from 'ws';
/**
 * A simple TypeScript client to test the relay server
 */

// Configuration
const RELAY_SERVER_URL = 'ws://localhost:8081';

// Interface definitions
interface RelayMessage {
  endpoint: string;
  [key: string]: any;
}

interface RelayResponse {
  status: number;
  data: any;
  error?: string;
}

// Main testing class
class RelayTester {
  private ws: WebSocket | null = null;

  // Connect to the relay server
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log(`Connecting to relay server at ${RELAY_SERVER_URL}...`);
      this.ws = new WebSocket(RELAY_SERVER_URL);
      
      this.ws.on('open', () => {
        console.log('Connected to relay server');
        resolve();
      });
      
      this.ws.on('error', (error: Error) => {
        console.error('WebSocket error:', error);
        reject(error);
      });
    });
  }

  // Send a message and wait for response
  sendMessage(message: RelayMessage): Promise<RelayResponse> {
    return new Promise((resolve, reject) => {
      if (!this.ws) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      // Set up one-time message handler for the response
      this.ws.once('message', (data: WebSocket.MessageEvent) => {
        try {
          const response = JSON.parse(data.toString()) as RelayResponse;
          resolve(response);
        } catch (error) {
          reject(new Error(`Failed to parse response: ${error}`));
        }
      });

      // Send the message
      console.log(`Sending message to endpoint: ${message.endpoint}`);
      this.ws.send(JSON.stringify(message));
    });
  }

  // Close the connection
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      console.log('Disconnected from relay server');
    }
  }

  // Test chat completions endpoint
  async testChatCompletions(): Promise<void> {
    console.log('\n--- Testing Chat Completions Endpoint ---');
    
    const message: RelayMessage = {
      endpoint: '/v1/chat/completions',
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: 'Hello, how are you?' }
      ]
    };

    try {
      const response = await this.sendMessage(message);
      console.log(`Response status: ${response.status}`);
      console.log('Response data:', JSON.stringify(response.data, null, 2).substring(0, 200) + '...');
      console.log('Chat completions test completed successfully');
    } catch (error) {
      console.error('Chat completions test failed:', error);
    }
  }

  // Test audio speech endpoint (text-to-speech)
  async testAudioSpeech(): Promise<void> {
    console.log('\n--- Testing Audio Speech Endpoint ---');
    
    const message: RelayMessage = {
      endpoint: '/v1/audio/speech',
      model: 'tts-1',
      input: 'Hello, this is a test of the audio speech API.',
      voice: 'alloy'
    };

    try {
      const response = await this.sendMessage(message);
      console.log(`Response status: ${response.status}`);
      if (response.data.type && response.data.data) {
        console.log(`Received binary data of type: ${response.data.type}`);
        console.log(`Data length: ${response.data.data.length} characters`);
        // Here we could save the base64 data as an audio file if needed
      } else {
        console.log('Response data:', response.data);
      }
      console.log('Audio speech test completed successfully');
    } catch (error) {
      console.error('Audio speech test failed:', error);
    }
  }

  // Test image generation endpoint
  async testImageGeneration(): Promise<void> {
    console.log('\n--- Testing Image Generation Endpoint ---');
    
    const message: RelayMessage = {
      endpoint: '/v1/images/generations',
      model: 'dall-e-3',
      prompt: 'A cute cat wearing a space helmet',
      n: 1,
      size: '1024x1024'
    };

    try {
      const response = await this.sendMessage(message);
      console.log(`Response status: ${response.status}`);
      console.log('Response data:', JSON.stringify(response.data, null, 2).substring(0, 200) + '...');
      
      // If we get a successful response with image URLs, we could download them here
      if (response.status === 200 && response.data.data && response.data.data[0]?.url) {
        console.log(`Image URL: ${response.data.data[0].url}`);
      }
      
      console.log('Image generation test completed successfully');
    } catch (error) {
      console.error('Image generation test failed:', error);
    }
  }

  // Run all tests
  async runAllTests(): Promise<void> {
    try {
      await this.connect();
      await this.testChatCompletions();
      await this.testAudioSpeech();
      await this.testImageGeneration();
    } catch (error) {
      console.error('Test suite failed:', error);
    } finally {
      this.disconnect();
    }
  }
}

// Run the tests
const tester = new RelayTester();
tester.runAllTests().catch(console.error); 