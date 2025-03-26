import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs';

// Helper function to get the current directory path
const getCurrentDirectory = () => path.resolve();

async function captureStreamFrame(url, outputFile) {
  return new Promise((resolve, reject) => {
    ffmpeg(url)
      .on('end', () => {
        console.log(`Screenshot saved as ${outputFile}`);
        resolve();
      })
      .on('error', (err) => {
        console.error(`Error: ${err}`);
        reject(err);
      })
      .screenshots({
        timestamps: ['00:00:01.000'], // Capture a frame at 1 second (adjust as needed)
        filename: path.basename(outputFile),
        folder: path.dirname(outputFile),
        size: '640x360', // Adjust the screenshot size
      });
  });
}

const screenshotsDir = path.join(getCurrentDirectory(), 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir);
}

const url = 'http://192.168.1.88:81/stream'; // Your local stream URL
const outputFile = path.join(screenshotsDir, 'stream_frame.png');
captureStreamFrame(url, outputFile).catch((err) => console.error(err));
