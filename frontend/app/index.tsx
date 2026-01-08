import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  StatusBar,
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions,
  TextInput,
  Modal,
  Switch,
  KeyboardAvoidingView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';

const { width } = Dimensions.get('window');

// API Configuration - hardcode for mobile compatibility
const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://context-aware-5.preview.emergentagent.com';

// Recording interval in milliseconds (how often to process audio)
const RECORDING_INTERVAL = 8000; // 8 seconds chunks for better transcription

// Types
type Mode = 'interview' | 'business' | 'sales' | 'general';
type Screen = 'home' | 'session' | 'history' | 'sessionDetail';

interface Suggestion {
  text: string;
  tone: string;
  priority: number;
}

interface SavedSuggestion {
  id: string;
  session_id: string;
  text: string;
  tone: string;
  timestamp: string;
  tags: string[];
}

interface Note {
  id: string;
  session_id: string;
  text: string;
  suggestion_ids: string[];
  created_at: string;
  updated_at: string;
}

interface SessionHistory {
  id: string;
  mode: string;
  duration: number;
  transcript_enabled: boolean;
  saved_suggestions_count: number;
  notes_count: number;
  created_at: string;
}

interface ModeConfig {
  id: Mode;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  description: string;
}

interface Settings {
  hapticEnabled: boolean;
  transcriptEnabled: boolean;
}

// Mode Configurations
const MODES: ModeConfig[] = [
  {
    id: 'interview',
    label: 'Interview',
    icon: 'briefcase-outline',
    color: '#6366F1',
    description: 'Job interviews & professional assessments',
  },
  {
    id: 'business',
    label: 'Business',
    icon: 'business-outline',
    color: '#10B981',
    description: 'Meetings, negotiations & corporate discussions',
  },
  {
    id: 'sales',
    label: 'Sales',
    icon: 'trending-up-outline',
    color: '#F59E0B',
    description: 'Client pitches & sales conversations',
  },
  {
    id: 'general',
    label: 'General',
    icon: 'chatbubbles-outline',
    color: '#8B5CF6',
    description: 'Everyday conversations & casual chats',
  },
];

// Settings storage key
const SETTINGS_KEY = '@whisprly_settings';

export default function WhisprlyApp() {
  // State
  const [currentScreen, setCurrentScreen] = useState<Screen>('home');
  const [selectedMode, setSelectedMode] = useState<Mode>('general');
  const [sessionId, setSessionId] = useState<string>('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [detectedQuestion, setDetectedQuestion] = useState(false);
  const [questionContext, setQuestionContext] = useState<string | null>(null);
  const [conversationContext, setConversationContext] = useState<string[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [fullTranscript, setFullTranscript] = useState('');
  const [sessionDuration, setSessionDuration] = useState(0);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // History state
  const [sessionHistoryList, setSessionHistoryList] = useState<SessionHistory[]>([]);
  const [selectedHistorySession, setSelectedHistorySession] = useState<SessionHistory | null>(null);
  const [savedSuggestions, setSavedSuggestions] = useState<SavedSuggestion[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  
  // Settings state
  const [settings, setSettings] = useState<Settings>({
    hapticEnabled: true,
    transcriptEnabled: false,
  });

  // Refs
  const recordingRef = useRef<Audio.Recording | null>(null);
  const sessionTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastHapticRef = useRef<number>(0);
  const previousSuggestionsLengthRef = useRef<number>(0);
  const isListeningRef = useRef<boolean>(false);
  
  // Animations
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const toastAnim = useRef(new Animated.Value(0)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const stored = await AsyncStorage.getItem(SETTINGS_KEY);
      if (stored) {
        setSettings(JSON.parse(stored));
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const saveSettings = async (newSettings: Settings) => {
    try {
      await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(newSettings));
      setSettings(newSettings);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  // Haptic feedback with rate limiting (max once every 3 seconds)
  const triggerHaptic = useCallback(() => {
    if (!settings.hapticEnabled) return;
    
    const now = Date.now();
    if (now - lastHapticRef.current >= 3000) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      lastHapticRef.current = now;
    }
  }, [settings.hapticEnabled]);

  // Trigger haptic when new suggestions arrive
  useEffect(() => {
    if (suggestions.length > 0 && suggestions.length !== previousSuggestionsLengthRef.current) {
      triggerHaptic();
      previousSuggestionsLengthRef.current = suggestions.length;
    }
  }, [suggestions, triggerHaptic]);

  // Pulse animation for listening indicator
  useEffect(() => {
    if (isListening) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.3,
            duration: 600,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 600,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      
      // Wave animation for visual feedback
      const wave = Animated.loop(
        Animated.sequence([
          Animated.timing(waveAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(waveAnim, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      );
      wave.start();
      
      return () => {
        pulse.stop();
        wave.stop();
      };
    }
  }, [isListening, pulseAnim, waveAnim]);

  // Fade in suggestions
  useEffect(() => {
    if (suggestions.length > 0) {
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [suggestions, fadeAnim]);

  // Session duration timer
  useEffect(() => {
    if (currentScreen === 'session' && sessionId) {
      sessionTimerRef.current = setInterval(() => {
        setSessionDuration((prev) => prev + 1);
      }, 1000);
      
      return () => {
        if (sessionTimerRef.current) {
          clearInterval(sessionTimerRef.current);
        }
      };
    }
  }, [currentScreen, sessionId]);

  // Toast animation
  const showToastMessage = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
    
    Animated.sequence([
      Animated.timing(toastAnim, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
      Animated.delay(1500),
      Animated.timing(toastAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start(() => setShowToast(false));
  };

  // API Functions
  const createSession = async (mode: Mode) => {
    try {
      console.log('Creating session with API_BASE_URL:', API_BASE_URL);
      const response = await fetch(`${API_BASE_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      const data = await response.json();
      console.log('Session created:', data);
      return data.id;
    } catch (error) {
      console.error('Failed to create session:', error);
      return `local_${Date.now()}`;
    }
  };

  const fetchSuggestions = async (text: string) => {
    if (!text.trim() || text.length < 10) {
      console.log('Text too short, skipping fetchSuggestions');
      return;
    }

    console.log('Fetching suggestions for:', text);
    setIsLoading(true);
    
    try {
      const requestBody = {
        transcript: text,
        mode: selectedMode,
        session_id: sessionId || `temp_${Date.now()}`,
        context: conversationContext,
      };
      
      const response = await fetch(`${API_BASE_URL}/api/suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API error:', errorText);
        throw new Error(`API request failed: ${errorText}`);
      }

      const data = await response.json();
      console.log('Suggestions received:', data);
      
      setSuggestions(data.suggestions || []);
      setDetectedQuestion(data.detected_question || false);
      setQuestionContext(data.question_context || null);
      setConversationContext((prev) => [...prev, text].slice(-10));
      
      if (data.detected_question) {
        showToastMessage('Question detected!');
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      setSuggestions([
        { text: 'Could you tell me more about that?', tone: 'curious', priority: 1 },
        { text: "That's interesting. I'd like to add...", tone: 'engaged', priority: 2 },
        { text: 'I understand your point.', tone: 'empathetic', priority: 3 },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const transcribeAudio = async (audioUri: string): Promise<string> => {
    try {
      console.log('Transcribing audio from:', audioUri);
      
      const base64Audio = await FileSystem.readAsStringAsync(audioUri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      
      console.log('Audio base64 length:', base64Audio.length);
      
      if (!base64Audio || base64Audio.length < 1000) {
        console.log('Audio too short, skipping transcription');
        return '';
      }
      
      const transcribeResponse = await fetch(`${API_BASE_URL}/api/transcribe-base64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          audio: base64Audio,
          language: 'en'
        }),
      });
      
      const data = await transcribeResponse.json();
      console.log('Transcription response:', data);
      
      if (data.success && data.text && data.text.trim()) {
        return data.text.trim();
      } else {
        console.log('No transcription text or error:', data.error);
        return '';
      }
    } catch (error) {
      console.error('Transcription error:', error);
      return '';
    }
  };

  // REAL-TIME CONTINUOUS LISTENING
  const startContinuousListening = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Please grant microphone access to listen to meetings.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      setIsListening(true);
      isListeningRef.current = true;
      setLiveTranscript('Listening to meeting...');
      showToastMessage('Real-time listening started!');
      
      // Start the first recording
      await startNewRecordingChunk();
      
      // Set up interval to process chunks
      recordingIntervalRef.current = setInterval(async () => {
        if (isListeningRef.current) {
          await processAndRestartRecording();
        }
      }, RECORDING_INTERVAL);
      
    } catch (error) {
      console.error('Failed to start continuous listening:', error);
      Alert.alert('Error', 'Failed to start listening. Please try again.');
      setIsListening(false);
      isListeningRef.current = false;
    }
  };

  const startNewRecordingChunk = async () => {
    try {
      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync({
        android: {
          extension: '.m4a',
          outputFormat: Audio.AndroidOutputFormat.MPEG_4,
          audioEncoder: Audio.AndroidAudioEncoder.AAC,
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
        },
        ios: {
          extension: '.m4a',
          audioQuality: Audio.IOSAudioQuality.MEDIUM,
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
          linearPCMBitDepth: 16,
          linearPCMIsBigEndian: false,
          linearPCMIsFloat: false,
        },
        web: {
          mimeType: 'audio/webm',
          bitsPerSecond: 64000,
        },
      });
      await recording.startAsync();
      recordingRef.current = recording;
      console.log('New recording chunk started');
    } catch (error) {
      console.error('Failed to start new recording chunk:', error);
    }
  };

  const processAndRestartRecording = async () => {
    if (!isListeningRef.current) return;
    
    try {
      setIsProcessing(true);
      
      // Stop current recording
      if (recordingRef.current) {
        await recordingRef.current.stopAndUnloadAsync();
        const uri = recordingRef.current.getURI();
        recordingRef.current = null;
        
        // Start new recording immediately (don't wait for processing)
        if (isListeningRef.current) {
          await startNewRecordingChunk();
        }
        
        // Process the audio in background
        if (uri) {
          const transcribedText = await transcribeAudio(uri);
          
          if (transcribedText && transcribedText.length > 5) {
            console.log('Transcribed:', transcribedText);
            setLiveTranscript(transcribedText);
            
            // Add to full transcript
            setFullTranscript(prev => {
              const updated = prev ? `${prev} ${transcribedText}` : transcribedText;
              return updated.slice(-500); // Keep last 500 chars
            });
            
            // Fetch suggestions based on new text
            await fetchSuggestions(transcribedText);
          }
        }
      }
    } catch (error) {
      console.error('Error processing recording chunk:', error);
      // Try to restart recording
      if (isListeningRef.current) {
        await startNewRecordingChunk();
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const stopContinuousListening = async () => {
    try {
      isListeningRef.current = false;
      setIsListening(false);
      
      // Clear interval
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
      
      // Stop current recording
      if (recordingRef.current) {
        try {
          await recordingRef.current.stopAndUnloadAsync();
        } catch (e) {
          console.log('Error stopping recording:', e);
        }
        recordingRef.current = null;
      }
      
      setLiveTranscript('');
      showToastMessage('Listening stopped');
      
    } catch (error) {
      console.error('Failed to stop listening:', error);
    }
  };

  const fetchSessionHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions`);
      const data = await response.json();
      setSessionHistoryList(data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const fetchSessionDetails = async (historySessionId: string) => {
    try {
      const [suggestionsRes, notesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/suggestions/saved/${historySessionId}`),
        fetch(`${API_BASE_URL}/api/notes/${historySessionId}`),
      ]);
      
      const suggestionsData = await suggestionsRes.json();
      const notesData = await notesRes.json();
      
      setSavedSuggestions(suggestionsData);
      setNotes(notesData);
    } catch (error) {
      console.error('Failed to fetch session details:', error);
    }
  };

  const saveSuggestion = async (suggestion: Suggestion) => {
    try {
      await fetch(`${API_BASE_URL}/api/suggestions/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          text: suggestion.text,
          tone: suggestion.tone,
        }),
      });
      showToastMessage('Suggestion saved!');
      triggerHaptic();
    } catch (error) {
      console.error('Failed to save suggestion:', error);
    }
  };

  const createNote = async () => {
    if (!noteText.trim()) return;
    
    try {
      const url = editingNoteId 
        ? `${API_BASE_URL}/api/notes/${editingNoteId}`
        : `${API_BASE_URL}/api/notes`;
      
      await fetch(url, {
        method: editingNoteId ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: selectedHistorySession?.id || sessionId,
          text: noteText,
        }),
      });
      
      setNoteText('');
      setEditingNoteId(null);
      setShowNoteModal(false);
      
      if (selectedHistorySession) {
        fetchSessionDetails(selectedHistorySession.id);
      }
      
      showToastMessage(editingNoteId ? 'Note updated!' : 'Note created!');
    } catch (error) {
      console.error('Failed to save note:', error);
    }
  };

  const deleteSession = async (deleteSessionId: string) => {
    try {
      await fetch(`${API_BASE_URL}/api/sessions/${deleteSessionId}`, {
        method: 'DELETE',
      });
      fetchSessionHistory();
      setCurrentScreen('history');
      showToastMessage('Session deleted');
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const deleteAllData = async () => {
    Alert.alert(
      'Delete All Data',
      'This will permanently delete all your sessions, suggestions, and notes. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete All',
          style: 'destructive',
          onPress: async () => {
            try {
              await fetch(`${API_BASE_URL}/api/sessions`, { method: 'DELETE' });
              fetchSessionHistory();
              showToastMessage('All data deleted');
            } catch (error) {
              console.error('Failed to delete all data:', error);
            }
          },
        },
      ]
    );
  };

  // Handle simulate input
  const handleSimulateInput = async () => {
    console.log('Simulate input tapped');
    const sampleInputs = [
      "Can you tell me about your experience with project management?",
      "What makes your product different from competitors?",
      "How would you handle a difficult team member?",
      "What are your thoughts on the budget proposal?",
      "Could you walk me through your sales process?",
      "What's your biggest professional achievement?",
      "How do you prioritize tasks when everything seems urgent?",
      "What salary range are you expecting for this position?",
    ];
    const randomInput = sampleInputs[Math.floor(Math.random() * sampleInputs.length)];
    console.log('Selected input:', randomInput);
    setLiveTranscript(randomInput);
    await fetchSuggestions(randomInput);
  };

  // Clipboard Function
  const copyToClipboard = async (text: string) => {
    try {
      await Clipboard.setStringAsync(text);
      showToastMessage('Copied!');
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  // Navigation Functions
  const handleStartSession = async (mode: Mode) => {
    console.log('Starting session with mode:', mode);
    setSelectedMode(mode);
    const newSessionId = await createSession(mode);
    setSessionId(newSessionId);
    setSuggestions([]);
    setConversationContext([]);
    setDetectedQuestion(false);
    setQuestionContext(null);
    setSessionDuration(0);
    setLiveTranscript('');
    setFullTranscript('');
    setCurrentScreen('session');
  };

  const handleEndSession = async () => {
    await stopContinuousListening();
    
    // Update session duration
    try {
      await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration: sessionDuration }),
      });
    } catch (error) {
      console.error('Failed to update session:', error);
    }
    
    setSuggestions([]);
    setConversationContext([]);
    setSessionId('');
    setCurrentScreen('home');
  };

  const handleViewHistory = () => {
    fetchSessionHistory();
    setCurrentScreen('history');
  };

  const handleViewSessionDetail = (session: SessionHistory) => {
    setSelectedHistorySession(session);
    fetchSessionDetails(session.id);
    setCurrentScreen('sessionDetail');
  };

  // Format duration
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get mode config
  const getModeConfig = (mode: string) => MODES.find((m) => m.id === mode) || MODES[3];

  // Render Toast
  const renderToast = () => {
    if (!showToast) return null;
    
    return (
      <Animated.View
        style={[
          styles.toast,
          {
            opacity: toastAnim,
            transform: [{ translateY: toastAnim.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }],
          },
        ]}
      >
        <Ionicons name="checkmark-circle" size={18} color="#10B981" />
        <Text style={styles.toastText}>{toastMessage}</Text>
      </Animated.View>
    );
  };

  // Render Settings Modal
  const renderSettingsModal = () => (
    <Modal visible={showSettingsModal} transparent animationType="slide">
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Settings</Text>
            <TouchableOpacity onPress={() => setShowSettingsModal(false)}>
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Ionicons name="phone-portrait-outline" size={22} color="#8B5CF6" />
              <View style={styles.settingTextContainer}>
                <Text style={styles.settingLabel}>Haptic Feedback</Text>
                <Text style={styles.settingDescription}>Vibrate when new suggestions arrive</Text>
              </View>
            </View>
            <Switch
              value={settings.hapticEnabled}
              onValueChange={(value) => saveSettings({ ...settings, hapticEnabled: value })}
              trackColor={{ false: '#374151', true: '#8B5CF620' }}
              thumbColor={settings.hapticEnabled ? '#8B5CF6' : '#6B7280'}
            />
          </View>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Ionicons name="document-text-outline" size={22} color="#8B5CF6" />
              <View style={styles.settingTextContainer}>
                <Text style={styles.settingLabel}>Save Transcripts</Text>
                <Text style={styles.settingDescription}>Store conversation transcripts (privacy)</Text>
              </View>
            </View>
            <Switch
              value={settings.transcriptEnabled}
              onValueChange={(value) => saveSettings({ ...settings, transcriptEnabled: value })}
              trackColor={{ false: '#374151', true: '#8B5CF620' }}
              thumbColor={settings.transcriptEnabled ? '#8B5CF6' : '#6B7280'}
            />
          </View>
          
          <TouchableOpacity style={styles.dangerButton} onPress={deleteAllData}>
            <Ionicons name="trash-outline" size={20} color="#EF4444" />
            <Text style={styles.dangerButtonText}>Delete All Data</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  // Render Note Modal
  const renderNoteModal = () => (
    <Modal visible={showNoteModal} transparent animationType="slide">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.modalOverlay}
      >
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{editingNoteId ? 'Edit Note' : 'New Note'}</Text>
            <TouchableOpacity onPress={() => { setShowNoteModal(false); setNoteText(''); setEditingNoteId(null); }}>
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
          
          <TextInput
            style={styles.noteInput}
            placeholder="Write your note..."
            placeholderTextColor="#6B7280"
            multiline
            value={noteText}
            onChangeText={setNoteText}
          />
          
          <TouchableOpacity style={styles.saveButton} onPress={createNote}>
            <Text style={styles.saveButtonText}>Save Note</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );

  // Render Home Screen
  const renderHomeScreen = () => (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.homeHeader}>
        <View style={styles.logoContainer}>
          <Ionicons name="ear-outline" size={32} color="#8B5CF6" />
          <Text style={styles.logoText}>Whisprly</Text>
        </View>
        <Text style={styles.tagline}>Real-time meeting assistant</Text>
        
        <View style={styles.headerActions}>
          <TouchableOpacity style={styles.headerButton} onPress={handleViewHistory}>
            <Ionicons name="time-outline" size={22} color="#FFFFFF" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.headerButton} onPress={() => setShowSettingsModal(true)}>
            <Ionicons name="settings-outline" size={22} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Mode Selection */}
      <View style={styles.modesContainer}>
        <Text style={styles.sectionTitle}>Select Mode</Text>
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.modesScrollContent}
        >
          {MODES.map((mode) => (
            <TouchableOpacity
              key={mode.id}
              style={[styles.modeCard, { borderColor: mode.color }]}
              onPress={() => handleStartSession(mode.id)}
              activeOpacity={0.7}
            >
              <View style={[styles.modeIconContainer, { backgroundColor: `${mode.color}20` }]}>
                <Ionicons name={mode.icon} size={28} color={mode.color} />
              </View>
              <View style={styles.modeTextContainer}>
                <Text style={styles.modeLabel}>{mode.label}</Text>
                <Text style={styles.modeDescription}>{mode.description}</Text>
              </View>
              <Ionicons name="chevron-forward" size={24} color="#6B7280" />
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Footer */}
      <View style={styles.homeFooter}>
        <Text style={styles.footerText}>
          Tap a mode to start listening to your meeting
        </Text>
      </View>
      
      {renderSettingsModal()}
      {renderToast()}
    </SafeAreaView>
  );

  // Render Session Screen
  const renderSessionScreen = () => {
    const modeConfig = getModeConfig(selectedMode);

    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />

        {/* Session Header */}
        <View style={styles.sessionHeader}>
          <TouchableOpacity onPress={handleEndSession} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
          </TouchableOpacity>
          <View style={styles.sessionHeaderCenter}>
            <View style={[styles.modeBadge, { backgroundColor: `${modeConfig.color}20` }]}>
              <Ionicons name={modeConfig.icon} size={16} color={modeConfig.color} />
              <Text style={[styles.modeBadgeText, { color: modeConfig.color }]}>
                {modeConfig.label}
              </Text>
            </View>
            <Text style={styles.durationText}>{formatDuration(sessionDuration)}</Text>
          </View>
          <View style={styles.headerSpacer} />
        </View>

        {/* Listening Status Bar */}
        {isListening && (
          <View style={styles.listeningStatusBar}>
            <Animated.View 
              style={[
                styles.listeningWave,
                {
                  opacity: waveAnim.interpolate({ inputRange: [0, 1], outputRange: [0.3, 1] }),
                  transform: [{ scaleX: waveAnim.interpolate({ inputRange: [0, 1], outputRange: [0.8, 1.2] }) }],
                }
              ]}
            />
            <View style={styles.listeningDotActive} />
            <Text style={styles.listeningStatusText}>
              {isProcessing ? 'Processing...' : 'Listening to meeting...'}
            </Text>
          </View>
        )}

        {/* Live Transcript */}
        {liveTranscript ? (
          <View style={styles.transcriptBox}>
            <Ionicons name="chatbubble-outline" size={16} color="#8B5CF6" />
            <Text style={styles.transcriptText} numberOfLines={3}>{liveTranscript}</Text>
          </View>
        ) : null}

        {/* Question Alert */}
        {detectedQuestion && questionContext && (
          <View style={styles.questionAlert}>
            <Ionicons name="alert-circle" size={20} color="#F59E0B" />
            <Text style={styles.questionAlertText}>
              {questionContext}
            </Text>
          </View>
        )}

        {/* Suggestions Area */}
        <ScrollView
          style={styles.suggestionsContainer}
          contentContainerStyle={styles.suggestionsContent}
          showsVerticalScrollIndicator={false}
        >
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#8B5CF6" />
              <Text style={styles.loadingText}>Generating suggestions...</Text>
            </View>
          ) : suggestions.length > 0 ? (
            <Animated.View style={{ opacity: fadeAnim }}>
              <Text style={styles.suggestionsTitle}>Suggested Responses</Text>
              {suggestions.map((suggestion, index) => (
                <View key={index} style={styles.suggestionCard}>
                  <View style={styles.suggestionHeader}>
                    <View style={styles.priorityBadge}>
                      <Text style={styles.priorityText}>#{suggestion.priority}</Text>
                    </View>
                    <View style={styles.toneBadge}>
                      <Text style={styles.toneText}>{suggestion.tone}</Text>
                    </View>
                  </View>
                  <Text style={styles.suggestionText}>{suggestion.text}</Text>
                  <View style={styles.suggestionActions}>
                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => copyToClipboard(suggestion.text)}
                    >
                      <Ionicons name="copy-outline" size={18} color="#8B5CF6" />
                      <Text style={styles.actionButtonText}>Copy</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => saveSuggestion(suggestion)}
                    >
                      <Ionicons name="bookmark-outline" size={18} color="#10B981" />
                      <Text style={[styles.actionButtonText, { color: '#10B981' }]}>Save</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </Animated.View>
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="mic-outline" size={56} color="#4B5563" />
              <Text style={styles.emptyStateTitle}>Ready to assist</Text>
              <Text style={styles.emptyStateText}>
                Tap the microphone button below to start{'\n'}
                listening to your meeting in real-time
              </Text>
              <View style={styles.instructionBox}>
                <Text style={styles.instructionTitle}>How it works:</Text>
                <Text style={styles.instructionText}>1. Tap the mic to start listening</Text>
                <Text style={styles.instructionText}>2. The app will hear your meeting</Text>
                <Text style={styles.instructionText}>3. Get instant response suggestions</Text>
              </View>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <TouchableOpacity
            style={styles.simulateButton}
            onPress={handleSimulateInput}
            activeOpacity={0.7}
          >
            <Ionicons name="flash-outline" size={20} color="#6B7280" />
            <Text style={styles.simulateButtonText}>Test with sample</Text>
          </TouchableOpacity>

          {/* Microphone Button - Main Control */}
          <TouchableOpacity
            style={[
              styles.micButton,
              isListening && styles.micButtonActive,
              { backgroundColor: isListening ? '#EF4444' : modeConfig.color },
            ]}
            onPress={isListening ? stopContinuousListening : startContinuousListening}
            activeOpacity={0.7}
          >
            <Animated.View style={{ transform: [{ scale: isListening ? pulseAnim : 1 }] }}>
              <Ionicons
                name={isListening ? 'stop' : 'mic'}
                size={32}
                color="#FFFFFF"
              />
            </Animated.View>
          </TouchableOpacity>
        </View>

        {/* Bottom Hint */}
        <View style={styles.bottomHint}>
          <Text style={styles.bottomHintText}>
            {isListening ? 'Tap the red button to stop listening' : 'Tap the mic to start real-time listening'}
          </Text>
        </View>
        
        {renderToast()}
      </SafeAreaView>
    );
  };

  // Render History Screen
  const renderHistoryScreen = () => (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <View style={styles.historyHeader}>
        <TouchableOpacity onPress={() => setCurrentScreen('home')} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.historyTitle}>History</Text>
        <View style={styles.headerSpacer} />
      </View>
      
      <ScrollView style={styles.historyList} contentContainerStyle={styles.historyListContent}>
        {sessionHistoryList.length === 0 ? (
          <View style={styles.emptyHistory}>
            <Ionicons name="folder-open-outline" size={48} color="#4B5563" />
            <Text style={styles.emptyHistoryText}>No sessions yet</Text>
            <Text style={styles.emptyHistorySubtext}>Your conversation history will appear here</Text>
          </View>
        ) : (
          sessionHistoryList.map((session) => {
            const modeConfig = getModeConfig(session.mode);
            return (
              <TouchableOpacity
                key={session.id}
                style={styles.historyCard}
                onPress={() => handleViewSessionDetail(session)}
              >
                <View style={[styles.historyModeIcon, { backgroundColor: `${modeConfig.color}20` }]}>
                  <Ionicons name={modeConfig.icon} size={24} color={modeConfig.color} />
                </View>
                <View style={styles.historyCardContent}>
                  <Text style={styles.historyCardTitle}>{modeConfig.label}</Text>
                  <Text style={styles.historyCardDate}>{formatDate(session.created_at)}</Text>
                  <View style={styles.historyCardStats}>
                    <View style={styles.statItem}>
                      <Ionicons name="bookmark" size={14} color="#6B7280" />
                      <Text style={styles.statText}>{session.saved_suggestions_count}</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Ionicons name="document-text" size={14} color="#6B7280" />
                      <Text style={styles.statText}>{session.notes_count}</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Ionicons name="time" size={14} color="#6B7280" />
                      <Text style={styles.statText}>{formatDuration(session.duration)}</Text>
                    </View>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#6B7280" />
              </TouchableOpacity>
            );
          })
        )}
      </ScrollView>
      
      {renderToast()}
    </SafeAreaView>
  );

  // Render Session Detail Screen
  const renderSessionDetailScreen = () => {
    if (!selectedHistorySession) return null;
    
    const modeConfig = getModeConfig(selectedHistorySession.mode);
    
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        
        <View style={styles.historyHeader}>
          <TouchableOpacity onPress={() => setCurrentScreen('history')} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
          </TouchableOpacity>
          <View style={styles.sessionDetailTitle}>
            <Text style={styles.historyTitle}>{modeConfig.label}</Text>
            <Text style={styles.sessionDetailDate}>{formatDate(selectedHistorySession.created_at)}</Text>
          </View>
          <TouchableOpacity onPress={() => deleteSession(selectedHistorySession.id)}>
            <Ionicons name="trash-outline" size={22} color="#EF4444" />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.detailContent}>
          {/* Saved Suggestions Section */}
          <View style={styles.detailSection}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionHeaderText}>Saved Suggestions</Text>
              <Text style={styles.sectionCount}>{savedSuggestions.length}</Text>
            </View>
            
            {savedSuggestions.length === 0 ? (
              <Text style={styles.noItemsText}>No saved suggestions</Text>
            ) : (
              savedSuggestions.map((suggestion) => (
                <View key={suggestion.id} style={styles.savedSuggestionCard}>
                  <View style={styles.savedSuggestionHeader}>
                    <View style={styles.toneBadge}>
                      <Text style={styles.toneText}>{suggestion.tone}</Text>
                    </View>
                    <TouchableOpacity onPress={() => copyToClipboard(suggestion.text)}>
                      <Ionicons name="copy-outline" size={18} color="#8B5CF6" />
                    </TouchableOpacity>
                  </View>
                  <Text style={styles.savedSuggestionText}>{suggestion.text}</Text>
                </View>
              ))
            )}
          </View>
          
          {/* Notes Section */}
          <View style={styles.detailSection}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionHeaderText}>Notes</Text>
              <TouchableOpacity onPress={() => setShowNoteModal(true)}>
                <Ionicons name="add-circle" size={24} color="#8B5CF6" />
              </TouchableOpacity>
            </View>
            
            {notes.length === 0 ? (
              <Text style={styles.noItemsText}>No notes yet. Tap + to add one.</Text>
            ) : (
              notes.map((note) => (
                <View key={note.id} style={styles.noteCard}>
                  <Text style={styles.noteText}>{note.text}</Text>
                  <View style={styles.noteActions}>
                    <TouchableOpacity
                      onPress={() => {
                        setNoteText(note.text);
                        setEditingNoteId(note.id);
                        setShowNoteModal(true);
                      }}
                    >
                      <Ionicons name="pencil-outline" size={18} color="#6B7280" />
                    </TouchableOpacity>
                  </View>
                </View>
              ))
            )}
          </View>
        </ScrollView>
        
        {renderNoteModal()}
        {renderToast()}
      </SafeAreaView>
    );
  };

  // Main render
  switch (currentScreen) {
    case 'session':
      return renderSessionScreen();
    case 'history':
      return renderHistoryScreen();
    case 'sessionDetail':
      return renderSessionDetailScreen();
    default:
      return renderHomeScreen();
  }
}

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F0F14',
  },
  
  // Home Screen Styles
  homeHeader: {
    alignItems: 'center',
    paddingTop: Platform.OS === 'android' ? 40 : 20,
    paddingBottom: 24,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logoText: {
    fontSize: 32,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -1,
  },
  tagline: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 8,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  headerButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#1A1A24',
    alignItems: 'center',
    justifyContent: 'center',
  },
  
  modesContainer: {
    flex: 1,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  modesScrollContent: {
    paddingBottom: 20,
  },
  modeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2D2D3A',
  },
  modeIconContainer: {
    width: 52,
    height: 52,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeTextContainer: {
    flex: 1,
    marginLeft: 14,
  },
  modeLabel: {
    fontSize: 17,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  modeDescription: {
    fontSize: 13,
    color: '#9CA3AF',
    lineHeight: 18,
  },
  
  homeFooter: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  footerText: {
    fontSize: 13,
    color: '#6B7280',
  },

  // Session Screen Styles
  sessionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'android' ? 40 : 12,
    paddingBottom: 12,
  },
  backButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionHeaderCenter: {
    flex: 1,
    alignItems: 'center',
  },
  headerSpacer: {
    width: 44,
  },
  modeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  modeBadgeText: {
    fontSize: 14,
    fontWeight: '600',
  },
  durationText: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },

  listeningStatusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#10B98120',
    marginHorizontal: 16,
    padding: 10,
    borderRadius: 12,
    marginBottom: 8,
    gap: 8,
    overflow: 'hidden',
  },
  listeningWave: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    backgroundColor: '#10B98110',
  },
  listeningDotActive: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#10B981',
  },
  listeningStatusText: {
    color: '#10B981',
    fontSize: 14,
    fontWeight: '600',
  },

  transcriptBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#1A1A24',
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 12,
    gap: 8,
    marginBottom: 8,
  },
  transcriptText: {
    flex: 1,
    color: '#D1D5DB',
    fontSize: 14,
    lineHeight: 20,
  },

  questionAlert: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 12,
    gap: 8,
    marginBottom: 8,
  },
  questionAlertText: {
    flex: 1,
    fontSize: 13,
    color: '#92400E',
    fontWeight: '500',
  },

  suggestionsContainer: {
    flex: 1,
  },
  suggestionsContent: {
    padding: 16,
  },
  suggestionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 12,
  },

  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    color: '#9CA3AF',
    marginTop: 12,
    fontSize: 14,
  },

  suggestionCard: {
    backgroundColor: '#1A1A24',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2D2D3A',
  },
  suggestionHeader: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  priorityBadge: {
    backgroundColor: '#8B5CF620',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  priorityText: {
    color: '#8B5CF6',
    fontSize: 12,
    fontWeight: '700',
  },
  toneBadge: {
    backgroundColor: '#374151',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  toneText: {
    color: '#D1D5DB',
    fontSize: 12,
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  suggestionText: {
    color: '#FFFFFF',
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 12,
  },
  suggestionActions: {
    flexDirection: 'row',
    gap: 16,
    borderTopWidth: 1,
    borderTopColor: '#2D2D3A',
    paddingTop: 12,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  actionButtonText: {
    color: '#8B5CF6',
    fontSize: 13,
    fontWeight: '500',
  },

  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyStateTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
  },
  emptyStateText: {
    color: '#6B7280',
    fontSize: 14,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
  },
  instructionBox: {
    backgroundColor: '#1A1A24',
    borderRadius: 12,
    padding: 16,
    marginTop: 24,
    width: '100%',
  },
  instructionTitle: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
  },
  instructionText: {
    color: '#9CA3AF',
    fontSize: 13,
    marginBottom: 6,
  },

  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: '#2D2D3A',
  },
  simulateButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    gap: 10,
  },
  simulateButtonText: {
    color: '#6B7280',
    fontSize: 14,
  },

  micButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  micButtonActive: {
    elevation: 8,
    shadowOpacity: 0.5,
  },

  bottomHint: {
    alignItems: 'center',
    paddingBottom: 16,
  },
  bottomHintText: {
    color: '#6B7280',
    fontSize: 12,
  },

  // Toast
  toast: {
    position: 'absolute',
    bottom: 140,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 8,
    borderWidth: 1,
    borderColor: '#10B98140',
  },
  toastText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '500',
  },

  // History Screen
  historyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'android' ? 40 : 12,
    paddingBottom: 16,
  },
  historyTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  historyList: {
    flex: 1,
  },
  historyListContent: {
    padding: 16,
  },
  emptyHistory: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyHistoryText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
  },
  emptyHistorySubtext: {
    color: '#6B7280',
    fontSize: 14,
    marginTop: 4,
  },
  historyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  },
  historyModeIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  historyCardContent: {
    flex: 1,
    marginLeft: 12,
  },
  historyCardTitle: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  historyCardDate: {
    color: '#6B7280',
    fontSize: 12,
    marginTop: 2,
  },
  historyCardStats: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 6,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    color: '#6B7280',
    fontSize: 12,
  },

  // Session Detail
  sessionDetailTitle: {
    flex: 1,
    alignItems: 'center',
  },
  sessionDetailDate: {
    color: '#6B7280',
    fontSize: 12,
    marginTop: 2,
  },
  detailContent: {
    flex: 1,
    padding: 16,
  },
  detailSection: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  sectionHeaderText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  sectionCount: {
    color: '#6B7280',
    fontSize: 14,
  },
  noItemsText: {
    color: '#6B7280',
    fontSize: 14,
    fontStyle: 'italic',
  },
  savedSuggestionCard: {
    backgroundColor: '#1A1A24',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  savedSuggestionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  savedSuggestionText: {
    color: '#D1D5DB',
    fontSize: 14,
    lineHeight: 20,
  },
  noteCard: {
    backgroundColor: '#1A1A24',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  noteText: {
    color: '#D1D5DB',
    fontSize: 14,
    lineHeight: 20,
  },
  noteActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
  },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1A1A24',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: Platform.OS === 'ios' ? 40 : 20,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  modalTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  noteInput: {
    backgroundColor: '#0F0F14',
    borderRadius: 12,
    padding: 14,
    color: '#FFFFFF',
    fontSize: 15,
    minHeight: 120,
    textAlignVertical: 'top',
  },
  saveButton: {
    backgroundColor: '#8B5CF6',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2D2D3A',
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  settingTextContainer: {
    flex: 1,
  },
  settingLabel: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '500',
  },
  settingDescription: {
    color: '#6B7280',
    fontSize: 12,
    marginTop: 2,
  },
  dangerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 24,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  dangerButtonText: {
    color: '#EF4444',
    fontSize: 15,
    fontWeight: '600',
  },
});
