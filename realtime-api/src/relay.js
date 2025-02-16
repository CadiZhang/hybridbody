import { WebSocketServer } from 'ws';
import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY environment variable is required');
}

const app = express();
app.use(cors());

const server = app.listen(8081, () => {
  console.log('Relay server running on http://localhost:8081');
});

const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  console.log('Client connected');

  ws.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      // Forward the message to OpenAI's API
      const response = await fetch('https://api.openai.com/v1/audio/speech', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(message)
      });
      
      // Forward the response back to the client
      const result = await response.json();
      ws.send(JSON.stringify(result));
    } catch (error) {
      console.error('Error:', error);
      ws.send(JSON.stringify({ error: error.message }));
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
  });
}); 