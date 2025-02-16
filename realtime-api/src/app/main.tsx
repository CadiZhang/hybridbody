/**
 * Running a local relay server will allow you to hide your API key
 * and run custom logic on the server
 *
 * Set the local relay server address to:
 * REACT_APP_LOCAL_RELAY_SERVER_URL=http://localhost:8081
 *
 * This will also require you to set OPENAI_API_KEY= in a `.env` file
 * You can run it with `npm run relay`, in parallel with `npm start`
 */
const LOCAL_RELAY_SERVER_URL: string =
  import.meta.env.VITE_LOCAL_RELAY_SERVER_URL || '';

import { useEffect, useRef, useCallback, useState } from 'react';
import {
  RealtimeClient,
  type FormattedItem,
  type RealtimeEvent,
} from 'openai-realtime-api';
import { WavRecorder, WavStreamPlayer } from '../lib/index.js';
import { instructions } from '../utils/conversation_config.js';
import { WavRenderer } from '../utils/wav_renderer';
import { X, Edit, Zap, ArrowUp, ArrowDown } from 'react-feather';
import { Button } from '../components/button/Button.tsx';
import { Toggle } from '../components/toggle/Toggle.tsx';
import { Map } from '../components/Map.tsx';

/******************************************************************************
 * Types
 ******************************************************************************/
type CustomRealtimeEvent = RealtimeEvent & {
  count?: number;
};

/**
 * Type for result from get_weather() function call
 */
interface Coordinates {
  lat: number;
  lng: number;
  location?: string;
  temperature?: {
    value: number;
    units: string;
  };
  wind_speed?: {
    value: number;
    units: string;
  };
}

export function App() {
  /******************************************************************************
   * API Key Handling
   ******************************************************************************/
  /**
   * Ask user for API Key
   * If we're using the local relay server, we don't need this
   */
  const apiKey = LOCAL_RELAY_SERVER_URL
    ? ''
    : localStorage.getItem('tmp::voice_api_key') ||
      prompt('OpenAI API Key') ||
      '';
  if (apiKey !== '') {
    localStorage.setItem('tmp::voice_api_key', apiKey);
  }

  /******************************************************************************
   * Core Service Refs
   ******************************************************************************/
  /**
   * Instantiate:
   * - WavRecorder (speech input)
   * - WavStreamPlayer (speech output)
   * - RealtimeClient (API client)
   */
  const wavRecorderRef = useRef<WavRecorder>(
    new WavRecorder({ sampleRate: 24000 }),
  );
  const wavStreamPlayerRef = useRef<WavStreamPlayer>(
    new WavStreamPlayer({ sampleRate: 24000 }),
  );
  const clientRef = useRef<RealtimeClient>(
    new RealtimeClient(
      LOCAL_RELAY_SERVER_URL
        ? { url: LOCAL_RELAY_SERVER_URL }
        : {
            apiKey: apiKey,
            dangerouslyAllowAPIKeyInBrowser: true,
          },
    ),
  );

  /******************************************************************************
   * UI Refs
   ******************************************************************************/
  /**
   * References for
   * - Rendering audio visualization (canvas)
   * - Autoscrolling event logs
   * - Timing delta for event log displays
   */
  const clientCanvasRef = useRef<HTMLCanvasElement>(null);
  const serverCanvasRef = useRef<HTMLCanvasElement>(null);
  const eventsScrollRef = useRef<HTMLDivElement>(null);
  const eventsScrollHeightRef = useRef(0);
  const conversationScrollRef = useRef<HTMLDivElement>(null);
  const conversationScrollHeightRef = useRef(0);
  const memoryScrollRef = useRef<HTMLDivElement>(null);
  const memoryScrollHeightRef = useRef(0);
  const startTimeRef = useRef<string>(new Date().toISOString());

  /******************************************************************************
   * State Management
   ******************************************************************************/
  /**
   * All of our variables for displaying application state
   * - items are all conversation items (dialog)
   * - realtimeEvents are event logs, which can be expanded
   * - memoryKv is for set_memory() function
   * - coords, marker are for get_weather() function
   */
  // Conversation State
  const [items, setItems] = useState<FormattedItem[]>([]);
  const [realtimeEvents, setRealtimeEvents] = useState<CustomRealtimeEvent[]>(
    [],
  );
  const [expandedEvents, setExpandedEvents] = useState<{
    [key: string]: boolean;
  }>({});
  
  // Connection State
  const [isConnected, setIsConnected] = useState(false);
  const [canPushToTalk, setCanPushToTalk] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  
  // Tool State
  const [memoryKv, setMemoryKv] = useState<{ [key: string]: any }>({});
  const [coords, setCoords] = useState<Coordinates | null>({
    lat: 37.775593,
    lng: -122.418137,
  });
  const [marker, setMarker] = useState<Coordinates | null>(null);

  /******************************************************************************
   * Utility Functions
   ******************************************************************************/
  const formatTime = useCallback((timestamp: string) => {
    const startTime = startTimeRef.current;
    const t0 = new Date(startTime).valueOf();
    const t1 = new Date(timestamp).valueOf();
    const delta = t1 - t0;
    const hs = Math.floor(delta / 10) % 100;
    const s = Math.floor(delta / 1000) % 60;
    const m = Math.floor(delta / 60_000) % 60;
    const pad = (n: number) => {
      let s = n + '';
      while (s.length < 2) {
        s = '0' + s;
      }
      return s;
    };
    return `${pad(m)}:${pad(s)}.${pad(hs)}`;
  }, []);

  /**
   * When you click the API key
   */
  const resetAPIKey = useCallback(() => {
    const apiKey = prompt('OpenAI API Key');
    if (apiKey !== null) {
      localStorage.clear();
      localStorage.setItem('tmp::voice_api_key', apiKey);
      window.location.reload();
    }
  }, []);

  /******************************************************************************
   * Event Handlers
   ******************************************************************************/
  /**
   * Connect to conversation:
   * WavRecorder taks speech input, WavStreamPlayer output, client is API client
   */
  const connectConversation = useCallback(async () => {
    const client = clientRef.current;
    const wavRecorder = wavRecorderRef.current;
    const wavStreamPlayer = wavStreamPlayerRef.current;

    // Set state variables
    startTimeRef.current = new Date().toISOString();
    setIsConnected(true);
    setRealtimeEvents([]);
    setItems(client.conversation.getItems());

    // Connect to microphone
    await wavRecorder.begin();

    // Connect to audio output
    await wavStreamPlayer.connect();

    // Connect to realtime API
    await client.connect();
    client.sendUserMessageContent([
      {
        type: `input_text`,
        text: `Hello!`,
        // text: `For testing purposes, I want you to list ten car brands. Number each item, e.g. "one (or whatever number you are one): the item name".`
      },
    ]);

    if (client.getTurnDetectionType() === 'server_vad') {
      await wavRecorder.record((data) => client.appendInputAudio(data.mono));
    }
  }, []);

  /**
   * Disconnect and reset conversation state
   */
  const disconnectConversation = useCallback(async () => {
    setIsConnected(false);
    setRealtimeEvents([]);
    setItems([]);
    setMemoryKv({});
    setCoords({
      lat: 37.775593,
      lng: -122.418137,
    });
    setMarker(null);

    const client = clientRef.current;
    client.disconnect();

    const wavRecorder = wavRecorderRef.current;
    await wavRecorder.end();

    const wavStreamPlayer = wavStreamPlayerRef.current;
    await wavStreamPlayer.interrupt();
  }, []);

  const deleteConversationItem = useCallback(async (id: string) => {
    const client = clientRef.current;
    client.deleteItem(id);
  }, []);

  /**
   * In push-to-talk mode, start recording
   * .appendInputAudio() for each sample
   */
  const startRecording = async () => {
    setIsRecording(true);
    const client = clientRef.current;
    const wavRecorder = wavRecorderRef.current;
    const wavStreamPlayer = wavStreamPlayerRef.current;
    const trackSampleOffset = await wavStreamPlayer.interrupt();
    if (trackSampleOffset?.trackId) {
      const { trackId, offset } = trackSampleOffset;
      await client.cancelResponse(trackId, offset);
    }
    await wavRecorder.record((data) => client.appendInputAudio(data.mono));
  };

  /**
   * In push-to-talk mode, stop recording
   */
  const stopRecording = async () => {
    setIsRecording(false);
    const client = clientRef.current;
    const wavRecorder = wavRecorderRef.current;
    await wavRecorder.pause();
    client.createResponse();
  };

  /**
   * Switch between Manual <> VAD mode for communication
   */
  const changeTurnEndType = async (value: string) => {
    const client = clientRef.current;
    const wavRecorder = wavRecorderRef.current;
    if (value === 'none' && wavRecorder.getStatus() === 'recording') {
      await wavRecorder.pause();
    }
    client.updateSession({
      turn_detection: value === 'none' ? null : { type: 'server_vad' },
    });
    if (value === 'server_vad' && client.isConnected) {
      await wavRecorder.record((data) => client.appendInputAudio(data.mono));
    }
    setCanPushToTalk(value === 'none');
  };

  /******************************************************************************
   * Effects
   ******************************************************************************/
  // Main effect for setting up event listeners
  
  useEffect(() => {
    // Get refs
    const wavStreamPlayer = wavStreamPlayerRef.current;
    const client = clientRef.current;

    // Set instructions
    client.updateSession({ instructions: instructions });
    // Set transcription, otherwise we don't get user transcriptions back
    client.updateSession({ input_audio_transcription: { model: 'whisper-1' } });

    // Add tools
    client.addTool(
      {
        name: 'set_memory',
        description: 'Saves important data about the user into memory.',
        parameters: {
          type: 'object',
          properties: {
            key: {
              type: 'string',
              description:
                'The key of the memory value. Always use lowercase and underscores, no other characters.',
            },
            value: {
              type: 'string',
              description: 'Value can be anything represented as a string',
            },
          },
          required: ['key', 'value'],
        },
      },
      async ({ key, value }: { [key: string]: any }) => {
        setMemoryKv((memoryKv) => {
          const newKv = { ...memoryKv };
          newKv[key] = value;
          return newKv;
        });
        return { ok: true };
      },
    );
    client.addTool(
      {
        name: 'get_weather',
        description:
          'Retrieves the weather for a given lat, lng coordinate pair. Specify a label for the location.',
        parameters: {
          type: 'object',
          properties: {
            lat: {
              type: 'number',
              description: 'Latitude',
            },
            lng: {
              type: 'number',
              description: 'Longitude',
            },
            location: {
              type: 'string',
              description: 'Name of the location',
            },
          },
          required: ['lat', 'lng', 'location'],
        },
      },
      async ({ lat, lng, location }: { [key: string]: any }) => {
        setMarker({ lat, lng, location });
        setCoords({ lat, lng, location });
        const result = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,wind_speed_10m`,
        );
        const json = await result.json();
        const temperature = {
          value: json.current.temperature_2m as number,
          units: json.current_units.temperature_2m as string,
        };
        const wind_speed = {
          value: json.current.wind_speed_10m as number,
          units: json.current_units.wind_speed_10m as string,
        };
        setMarker({ lat, lng, location, temperature, wind_speed });
        return json;
      },
    );

    // handle realtime events from client + server for event logging
    client.on('realtime.event', (realtimeEvent: CustomRealtimeEvent) => {
      setRealtimeEvents((realtimeEvents) => {
        const lastEvent = realtimeEvents[realtimeEvents.length - 1];
        if (lastEvent?.event.type === realtimeEvent.event.type) {
          // if we receive multiple events in a row, aggregate them for display purposes
          lastEvent.count = (lastEvent.count || 0) + 1;
          return realtimeEvents.slice(0, -1).concat(lastEvent);
        } else {
          return realtimeEvents.concat(realtimeEvent);
        }
      });
    });
    client.on('error', (event: any) => console.error(event));
    client.on('conversation.interrupted', async () => {
      const trackSampleOffset = await wavStreamPlayer.interrupt();
      if (trackSampleOffset?.trackId) {
        const { trackId, offset } = trackSampleOffset;
        await client.cancelResponse(trackId, offset);
      }
    });
    client.on('conversation.updated', async ({ item, delta }: any) => {
      const items = client.conversation.getItems();
      if (delta?.audio) {
        wavStreamPlayer.add16BitPCM(delta.audio, item.id);
      }
      if (item.status === 'completed' && item.formatted.audio?.length) {
        const wavFile = await WavRecorder.decode(
          item.formatted.audio,
          24000,
          24000,
        );
        item.formatted.file = wavFile;
      }
      setItems(items);
    });

    setItems(client.conversation.getItems());

    return () => {
      // cleanup; resets to defaults
      client.reset();
    };
  }, []);

  // Auto-scroll effects
  useEffect(() => {
    const scrollEl = conversationScrollRef.current;
    if (scrollEl) {
      // Only auto-scroll if we're already near the bottom
      const isNearBottom = 
        scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 100;
      
      if (isNearBottom || scrollEl.scrollHeight > conversationScrollHeightRef.current) {
        scrollEl.scrollTop = scrollEl.scrollHeight;
      }
      conversationScrollHeightRef.current = scrollEl.scrollHeight;
    }
  }, [items]); // Auto-scroll when items change

  // Auto-scroll effects for events
  useEffect(() => {
    const scrollEl = eventsScrollRef.current;
    if (scrollEl) {
      const isNearBottom = 
        scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 100;
      
      if (isNearBottom || scrollEl.scrollHeight > eventsScrollHeightRef.current) {
        scrollEl.scrollTop = scrollEl.scrollHeight;
      }
      eventsScrollHeightRef.current = scrollEl.scrollHeight;
    }
  }, [realtimeEvents]); // Auto-scroll when events change

  // Auto-scroll effects for memory
  useEffect(() => {
    const scrollEl = memoryScrollRef.current;
    if (scrollEl) {
      const isNearBottom = 
        scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 100;
      
      if (isNearBottom || scrollEl.scrollHeight > memoryScrollHeightRef.current) {
        scrollEl.scrollTop = scrollEl.scrollHeight;
      }
      memoryScrollHeightRef.current = scrollEl.scrollHeight;
    }
  }, [memoryKv]); // Auto-scroll when memory changes

  /**
   * Set up render loops for the visualization canvas
   */
  useEffect(() => {
    let isLoaded = true;

    const wavRecorder = wavRecorderRef.current;
    const clientCanvas = clientCanvasRef.current;
    let clientCtx: CanvasRenderingContext2D | null = null;

    const wavStreamPlayer = wavStreamPlayerRef.current;
    const serverCanvas = serverCanvasRef.current;
    let serverCtx: CanvasRenderingContext2D | null = null;

    const render = () => {
      if (isLoaded) {
        if (clientCanvas) {
          if (!clientCanvas.width || !clientCanvas.height) {
            clientCanvas.width = clientCanvas.offsetWidth;
            clientCanvas.height = clientCanvas.offsetHeight;
          }
          clientCtx = clientCtx || clientCanvas.getContext('2d');
          if (clientCtx) {
            clientCtx.clearRect(0, 0, clientCanvas.width, clientCanvas.height);
            const result = wavRecorder.recording
              ? wavRecorder.getFrequencies('voice')
              : { values: new Float32Array([0]) };
            WavRenderer.drawBars(
              clientCanvas,
              clientCtx,
              result.values,
              '#0099ff',
              10,
              0,
              8,
            );
          }
        }
        if (serverCanvas) {
          if (!serverCanvas.width || !serverCanvas.height) {
            serverCanvas.width = serverCanvas.offsetWidth;
            serverCanvas.height = serverCanvas.offsetHeight;
          }
          serverCtx = serverCtx || serverCanvas.getContext('2d');
          if (serverCtx) {
            serverCtx.clearRect(0, 0, serverCanvas.width, serverCanvas.height);
            const result = wavStreamPlayer.analyser
              ? wavStreamPlayer.getFrequencies('voice')
              : { values: new Float32Array([0]) };
            WavRenderer.drawBars(
              serverCanvas,
              serverCtx,
              result.values,
              '#009900',
              10,
              0,
              8,
            );
          }
        }
        window.requestAnimationFrame(render);
      }
    };
    render();

    return () => {
      isLoaded = false;
    };
  }, []);

  /******************************************************************************
   * Render
   ******************************************************************************/
  return (
    <div className="font-mono text-xs min-h-screen flex flex-col bg-white p-4">
      {/* Top header - improve alignment and spacing */}
      <div className="flex items-center justify-between px-6 h-14 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">realtime console</span>
        </div>
        <div>
          {!LOCAL_RELAY_SERVER_URL && (
            <Button
              icon={Edit}
              iconPosition="end"
              buttonStyle="flush"
              label={`api key: ${apiKey.slice(0, 3)}...`}
              onClick={() => resetAPIKey()}
            />
          )}
        </div>
      </div>

      {/* Main content - better spacing and shadows */}
      <div className="flex-1 flex gap-6 p-6">
        {/* Left panel */}
        <div className="flex-1 flex flex-col gap-6">
          {/* Events section */}
          <div className="h-[200px] flex flex-col rounded-2xl border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-medium">events</h2>
            </div>
            <div 
              className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent" 
              ref={eventsScrollRef}
            >
              {!realtimeEvents.length && (
                <div className="text-gray-400">awaiting connection...</div>
              )}
              {realtimeEvents.map((realtimeEvent) => (
                <div 
                  className="mb-3 last:mb-0 hover:bg-gray-50 rounded-lg transition-colors" 
                  key={realtimeEvent.event.event_id}
                >
                  <div className="rounded whitespace-pre flex p-2 gap-4">
                    <div className="text-left py-1 w-20 flex-shrink-0 mr-4 text-gray-500">
                      {formatTime(realtimeEvent.time)}
                    </div>
                    <div className="flex flex-col gap-2 min-w-0">
                      <div 
                        className="flex gap-2 items-center cursor-pointer"
                        onClick={() => {
                          const id = realtimeEvent.event.event_id!;
                          const expanded = { ...expandedEvents };
                          if (expanded[id]) {
                            delete expanded[id];
                          } else {
                            expanded[id] = true;
                          }
                          setExpandedEvents(expanded);
                        }}
                      >
                        <div className={`flex-shrink-0 flex items-center gap-2 
                          ${realtimeEvent.source === 'client' ? 'text-client' : 
                            realtimeEvent.source === 'server' ? 'text-server' : 
                            'text-error'}`}
                        >
                          {realtimeEvent.source === 'client' ? 
                            <ArrowUp className="w-3 h-3 stroke-[3]" /> : 
                            <ArrowDown className="w-3 h-3 stroke-[3]" />
                          }
                          <span>
                            {realtimeEvent.event.type === 'error' ? 'error!' : realtimeEvent.source}
                          </span>
                        </div>
                      </div>
                      {/* Event details when expanded */}
                      {expandedEvents[realtimeEvent.event.event_id!] && (
                        <div className="text-xs bg-gray-50 rounded-lg p-3 font-mono overflow-x-auto">
                          {JSON.stringify(realtimeEvent.event, null, 2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {/* Visualization overlay */}
            <div className="absolute bottom-4 right-4 flex gap-2">
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-2">
                <canvas ref={clientCanvasRef} className="w-24 h-10" />
              </div>
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-2">
                <canvas ref={serverCanvasRef} className="w-24 h-10" />
              </div>
            </div>
          </div>

          {/* Conversation section */}
          <div className="h-[200px] flex flex-col rounded-2xl border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-medium">conversation</h2>
            </div>
            <div 
              ref={conversationScrollRef}
              className="flex-1 overflow-auto p-4 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent"
            >
              {!items.length && (
                <div className="text-gray-400">awaiting connection...</div>
              )}
              {items.map((conversationItem) => (
                <div className="relative flex gap-4 mb-4 group" key={conversationItem.id}>
                  {/* Role label (user/assistant) */}
                  <div className={`relative text-left w-20 flex-shrink-0 mr-4
                    ${conversationItem.role === 'user' ? 'text-client' : 
                      conversationItem.role === 'assistant' ? 'text-server' : ''}`}>
                    <span>{conversationItem.role}</span>
                    
                    {/* Close button - only visible on hover */}
                    <div className="absolute top-0 right-[-20px] bg-gray-400 text-white rounded-2xl p-0.5 cursor-pointer 
                                   hidden group-hover:flex hover:bg-gray-600"
                                 onClick={() => deleteConversationItem(conversationItem.id)}>
                      <X className="w-3 h-3 stroke-[3]" />
                    </div>
                  </div>

                  {/* Message content */}
                  <div className="flex-1 min-w-0">
                    {conversationItem.formatted.tool && (
                      <div className="text-gray-600">
                        {conversationItem.formatted.text || '(function called)'}
                      </div>
                    )}
                    {!conversationItem.formatted.tool && conversationItem.role === 'user' && (
                      <div>
                        {conversationItem.formatted.transcript ||
                          (conversationItem.formatted.audio?.length
                            ? '(awaiting transcript)'
                            : conversationItem.formatted.text ||
                              '(item sent)')}
                      </div>
                    )}
                    {!conversationItem.formatted.tool && conversationItem.role === 'assistant' && (
                      <div>
                        {conversationItem.formatted.transcript ||
                          conversationItem.formatted.text ||
                          '(truncated)'}
                      </div>
                    )}
                    {conversationItem.formatted.file && (
                      <audio
                        src={conversationItem.formatted.file.url}
                        controls
                        className="mt-2"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between gap-4 p-4 rounded-2xl border border-gray-100">
            <Toggle
              defaultValue={false}
              labels={['manual', 'vad']}
              values={['none', 'server_vad']}
              onChange={(_, value) => changeTurnEndType(value)}
            />
            <div className="flex gap-4">
              {isConnected && canPushToTalk && (
                <Button
                  label={isRecording ? 'release to send' : 'push to talk'}
                  buttonStyle={isRecording ? 'alert' : 'regular'}
                  disabled={!isConnected || !canPushToTalk}
                  onMouseDown={startRecording}
                  onMouseUp={stopRecording}
                />
              )}
              <Button
                label={isConnected ? 'disconnect' : 'connect'}
                iconPosition={isConnected ? 'end' : 'start'}
                icon={isConnected ? X : Zap}
                buttonStyle={isConnected ? 'regular' : 'action'}
                onClick={isConnected ? disconnectConversation : connectConversation}
              />
            </div>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="w-[320px] flex flex-col gap-6">
          {/* Map widget */}
          <div className="flex-1 relative rounded-2xl border border-gray-100 overflow-hidden">
            <div className="absolute top-4 left-4 z-10">
              <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full">
                <span className="font-medium">get_weather()</span>
              </div>
            </div>
            {coords && <Map center={[coords.lat, coords.lng]} location={coords.location} />}
            {marker && (
              <div className="absolute bottom-4 right-4 z-10">
                <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full text-sm">
                  <div>{marker.location || 'not yet retrieved'}</div>
                  {marker.temperature && (
                    <div>🌡️ {marker.temperature.value} {marker.temperature.units}</div>
                  )}
                  {marker.wind_speed && (
                    <div>🍃 {marker.wind_speed.value} {marker.wind_speed.units}</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Memory widget */}
          <div className="h-[300px] flex flex-col rounded-2xl border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-medium">set_memory()</h2>
            </div>
            <div 
              ref={memoryScrollRef}
              className="flex-1 overflow-auto p-4 font-mono text-xs scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent"
            >
              {Object.keys(memoryKv).length === 0 ? (
                <div className="text-gray-400">no stored memories...</div>
              ) : (
                JSON.stringify(memoryKv, null, 2)
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
