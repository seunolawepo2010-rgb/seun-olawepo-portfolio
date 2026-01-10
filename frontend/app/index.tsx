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
  Dimensions,
  TextInput,
  Modal,
  Switch,
  KeyboardAvoidingView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';
import * as DocumentPicker from 'expo-document-picker';

const { width } = Dimensions.get('window');

// API Configuration
const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Recording interval in milliseconds (shorter = faster responses)
const RECORDING_INTERVAL = 4000; // 4 seconds chunks for faster responses

// Detect if running on web
const isWeb = Platform.OS === 'web';

// Types
type Mode = 'interview' | 'business' | 'sales' | 'general';
type Screen = 'home' | 'session' | 'history' | 'sessionDetail' | 'summary' | 'preferences' | 'knowledge';
type RecordingState = 'idle' | 'recording' | 'paused' | 'processing';

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

// Response Preferences Types
interface ResponsePreferences {
  tone: 'confident' | 'neutral' | 'executive' | 'friendly' | 'concise';
  style: 'direct' | 'explanation' | 'followup' | 'star';
  risk_level: 'conservative' | 'balanced' | 'assertive';
  role_type: string | null;
  seniority_level: 'ic' | 'manager' | 'director' | null;
  preferred_frameworks: string[];
}

interface ActionItem {
  task: string;
  owner: string | null;
  due_date: string | null;
}

interface MeetingSummary {
  summary_points: string[];
  action_items: ActionItem[];
  key_highlights: string[];
  mode: string;
  duration: number;
}

interface Settings {
  hapticEnabled: boolean;
  transcriptEnabled: boolean;
}

// Knowledge Base types
interface KnowledgeDocument {
  id: string;
  name: string;
  file_type: string;
  storage_type: 'persistent' | 'session';
  content_preview: string;
  file_size: number;
  created_at: string;
}

interface KnowledgeNote {
  id: string;
  title: string;
  storage_type: 'persistent' | 'session';
  content_preview: string;
  created_at: string;
}

// Conversation history entry type
interface ConversationEntry {
  id: string;
  timestamp: Date;
  transcript: string;
  question: string | null;
  suggestions: Suggestion[];
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

const SETTINGS_KEY = '@whisprly_settings';
const PREFERENCES_KEY = '@whisprly_preferences';

// Preference options
const TONE_OPTIONS = [
  { value: 'confident', label: 'Confident', icon: 'shield-checkmark-outline' },
  { value: 'neutral', label: 'Neutral', icon: 'remove-outline' },
  { value: 'executive', label: 'Executive', icon: 'business-outline' },
  { value: 'friendly', label: 'Friendly', icon: 'happy-outline' },
  { value: 'concise', label: 'Concise', icon: 'flash-outline' },
];

const STYLE_OPTIONS = [
  { value: 'direct', label: 'Direct Only' },
  { value: 'explanation', label: 'With Explanation' },
  { value: 'followup', label: 'With Follow-up' },
  { value: 'star', label: 'STAR Format' },
];

const RISK_OPTIONS = [
  { value: 'conservative', label: 'Conservative', description: 'Safe, policy-aware' },
  { value: 'balanced', label: 'Balanced', description: 'Measured responses' },
  { value: 'assertive', label: 'Assertive', description: 'Bold, clear positions' },
];

const ROLE_OPTIONS = [
  'Product Manager', 'Software Engineer', 'Data Scientist', 'Designer', 
  'Sales', 'Marketing', 'GRC/Compliance', 'Finance', 'HR', 'Operations', 'Other'
];

const SENIORITY_OPTIONS = [
  { value: 'ic', label: 'Individual Contributor' },
  { value: 'manager', label: 'Manager' },
  { value: 'director', label: 'Director/Executive' },
];

const DEFAULT_PREFERENCES: ResponsePreferences = {
  tone: 'neutral',
  style: 'direct',
  risk_level: 'balanced',
  role_type: null,
  seniority_level: null,
  preferred_frameworks: [],
};

// Inactivity timeout for prompt (60 seconds)
const INACTIVITY_TIMEOUT = 60000;

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
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [fullTranscript, setFullTranscript] = useState('');
  const [sessionDuration, setSessionDuration] = useState(0);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  
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
  
  // Response Preferences state
  const [preferences, setPreferences] = useState<ResponsePreferences>(DEFAULT_PREFERENCES);
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  
  // Meeting Summary state
  const [meetingSummary, setMeetingSummary] = useState<MeetingSummary | null>(null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [showInactivityPrompt, setShowInactivityPrompt] = useState(false);
  
  // Conversation history during active session
  const [conversationHistory, setConversationHistory] = useState<ConversationEntry[]>([]);
  const scrollViewRef = useRef<ScrollView>(null);

  // Knowledge Base state
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeDocument[]>([]);
  const [knowledgeNotes, setKnowledgeNotes] = useState<KnowledgeNote[]>([]);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [showAddNoteModal, setShowAddNoteModal] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteStorageType, setNewNoteStorageType] = useState<'persistent' | 'session'>('persistent');

  // Refs
  const recordingRef = useRef<Audio.Recording | null>(null);
  const sessionTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastHapticRef = useRef<number>(0);
  const previousSuggestionsLengthRef = useRef<number>(0);
  const isRecordingRef = useRef<boolean>(false);
  const isPausedRef = useRef<boolean>(false);
  const lastActivityRef = useRef<number>(Date.now());
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Web Audio API refs (for browser support)
  const webMediaRecorderRef = useRef<MediaRecorder | null>(null);
  const webAudioChunksRef = useRef<Blob[]>([]);
  const webStreamRef = useRef<MediaStream | null>(null);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
    loadPreferences();
    loadKnowledgeBase();
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

  const loadPreferences = async () => {
    try {
      const stored = await AsyncStorage.getItem(PREFERENCES_KEY);
      if (stored) {
        setPreferences({ ...DEFAULT_PREFERENCES, ...JSON.parse(stored) });
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
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

  const savePreferences = async (newPreferences: ResponsePreferences) => {
    try {
      await AsyncStorage.setItem(PREFERENCES_KEY, JSON.stringify(newPreferences));
      setPreferences(newPreferences);
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  };

  // Knowledge Base functions
  const loadKnowledgeBase = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/knowledge?session_id=${sessionId || ''}`);
      const data = await response.json();
      setKnowledgeDocuments(data.documents || []);
      setKnowledgeNotes(data.notes || []);
    } catch (error) {
      console.error('Failed to load knowledge base:', error);
    }
  };

  const uploadDocument = async (storageType: 'persistent' | 'session' = 'persistent') => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
          'text/plain',
        ],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) {
        return;
      }

      const file = result.assets[0];
      
      // Check file size (10MB limit)
      if (file.size && file.size > 10 * 1024 * 1024) {
        Alert.alert('File too large', 'Maximum file size is 10MB');
        return;
      }

      setIsUploadingDoc(true);

      // Read file and upload
      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        type: file.mimeType || 'application/octet-stream',
        name: file.name,
      } as any);
      formData.append('storage_type', storageType);
      if (sessionId) {
        formData.append('session_id', sessionId);
      }

      const response = await fetch(`${API_BASE_URL}/api/knowledge/document`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      showToastMessage('Document uploaded successfully!');
      await loadKnowledgeBase();
    } catch (error: any) {
      console.error('Upload error:', error);
      Alert.alert('Upload Failed', error.message || 'Failed to upload document');
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const addNote = async () => {
    if (!newNoteTitle.trim() || !newNoteContent.trim()) {
      Alert.alert('Error', 'Please enter both title and content');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('title', newNoteTitle.trim());
      formData.append('content', newNoteContent.trim());
      formData.append('storage_type', newNoteStorageType);
      if (sessionId) {
        formData.append('session_id', sessionId);
      }

      const response = await fetch(`${API_BASE_URL}/api/knowledge/note`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to add note');
      }

      setNewNoteTitle('');
      setNewNoteContent('');
      setShowAddNoteModal(false);
      showToastMessage('Note added successfully!');
      await loadKnowledgeBase();
    } catch (error) {
      console.error('Add note error:', error);
      Alert.alert('Error', 'Failed to add note');
    }
  };

  const deleteDocument = async (docId: string) => {
    Alert.alert('Delete Document', 'Are you sure you want to delete this document?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await fetch(`${API_BASE_URL}/api/knowledge/document/${docId}`, { method: 'DELETE' });
            showToastMessage('Document deleted');
            await loadKnowledgeBase();
          } catch (error) {
            Alert.alert('Error', 'Failed to delete document');
          }
        },
      },
    ]);
  };

  const deleteNote = async (noteId: string) => {
    Alert.alert('Delete Note', 'Are you sure you want to delete this note?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await fetch(`${API_BASE_URL}/api/knowledge/note/${noteId}`, { method: 'DELETE' });
            showToastMessage('Note deleted');
            await loadKnowledgeBase();
          } catch (error) {
            Alert.alert('Error', 'Failed to delete note');
          }
        },
      },
    ]);
  };

  // Inactivity tracking
  const resetInactivityTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    setShowInactivityPrompt(false);
    
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    
    if (recordingState === 'recording') {
      inactivityTimerRef.current = setTimeout(() => {
        setShowInactivityPrompt(true);
      }, INACTIVITY_TIMEOUT);
    }
  }, [recordingState]);

  // Haptic feedback
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

  // Session duration timer
  useEffect(() => {
    if (currentScreen === 'session' && sessionId) {
      sessionTimerRef.current = setInterval(() => {
        setSessionDuration((prev) => prev + 1);
      }, 1000);
      return () => {
        if (sessionTimerRef.current) clearInterval(sessionTimerRef.current);
      };
    }
  }, [currentScreen, sessionId]);

  // Toast message helper
  const showToastMessage = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
    // Auto-hide after 2 seconds
    setTimeout(() => setShowToast(false), 2000);
  };

  // API Functions
  const createSession = async (mode: Mode) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      const data = await response.json();
      return data.id;
    } catch (error) {
      console.error('Failed to create session:', error);
      return `local_${Date.now()}`;
    }
  };

  const fetchSuggestions = async (text: string) => {
    if (!text.trim() || text.length < 5) return;

    // Reset inactivity timer on activity
    resetInactivityTimer();
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          mode: selectedMode,
          session_id: sessionId || `temp_${Date.now()}`,
          context: conversationContext,
          preferences: preferences,
        }),
      });

      if (!response.ok) throw new Error('API request failed');

      const data = await response.json();
      const newSuggestions = data.suggestions || [];
      
      // Update current suggestions (for latest display)
      setSuggestions(newSuggestions);
      setDetectedQuestion(data.detected_question || false);
      setQuestionContext(data.question_context || null);
      setConversationContext((prev) => [...prev, text].slice(-10));
      
      // Add to conversation history (persistent during session)
      if (newSuggestions.length > 0) {
        const newEntry: ConversationEntry = {
          id: `entry_${Date.now()}`,
          timestamp: new Date(),
          transcript: text,
          question: data.question_context || null,
          suggestions: newSuggestions,
        };
        setConversationHistory(prev => [...prev, newEntry]);
        
        // Auto-scroll to bottom after adding new entry
        setTimeout(() => {
          scrollViewRef.current?.scrollToEnd({ animated: true });
        }, 100);
      }
      
      if (data.detected_question) {
        showToastMessage('Question detected!');
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      showToastMessage('Failed to get suggestions');
    } finally {
      setIsLoading(false);
    }
  };

  // Generate meeting summary
  const generateMeetingSummary = async (): Promise<MeetingSummary | null> => {
    if (!fullTranscript || fullTranscript.length < 20) {
      showToastMessage('Not enough conversation to summarize');
      return null;
    }

    setIsGeneratingSummary(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/generate-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          full_transcript: fullTranscript,
          mode: selectedMode,
          duration: sessionDuration,
        }),
      });

      if (!response.ok) throw new Error('Failed to generate summary');

      const summary = await response.json();
      setMeetingSummary(summary);
      return summary;
    } catch (error) {
      console.error('Failed to generate summary:', error);
      showToastMessage('Failed to generate summary');
      return null;
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  // End meeting and show summary
  const handleEndMeeting = async () => {
    console.log('handleEndMeeting called');
    
    // Stop recording first
    await handleStopRecording();
    
    // Clear inactivity timer
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    setShowInactivityPrompt(false);
    
    // Update session in backend
    try {
      await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          duration: sessionDuration,
          ended_at: new Date().toISOString()
        }),
      });
    } catch (error) {
      console.error('Failed to update session:', error);
    }
    
    // Generate summary if there's enough transcript
    if (fullTranscript && fullTranscript.length >= 20) {
      console.log('Generating summary for transcript:', fullTranscript.substring(0, 50));
      await generateMeetingSummary();
      setCurrentScreen('summary');
    } else {
      // Not enough content for summary, show message and go to summary anyway
      console.log('Not enough transcript, showing empty summary');
      setMeetingSummary({
        summary_points: ['Session ended - no significant conversation to summarize'],
        action_items: [],
        key_highlights: [],
        mode: selectedMode,
        duration: sessionDuration
      });
      setCurrentScreen('summary');
    }
  };

  // Share summary as text
  const shareSummary = async () => {
    if (!meetingSummary) return;
    
    const modeConfig = MODES.find(m => m.id === selectedMode);
    let text = `📋 ${modeConfig?.label || 'Meeting'} Summary\n`;
    text += `Duration: ${formatDuration(sessionDuration)}\n\n`;
    
    text += `📌 Summary\n`;
    meetingSummary.summary_points.forEach((point, i) => {
      text += `${i + 1}. ${point}\n`;
    });
    
    if (meetingSummary.action_items.length > 0) {
      text += `\n✅ Action Items\n`;
      meetingSummary.action_items.forEach((item, i) => {
        text += `${i + 1}. ${item.task}`;
        if (item.owner) text += ` (Owner: ${item.owner})`;
        if (item.due_date) text += ` [Due: ${item.due_date}]`;
        text += `\n`;
      });
    }
    
    if (meetingSummary.key_highlights.length > 0) {
      text += `\n⚡ Key Highlights\n`;
      meetingSummary.key_highlights.forEach((highlight, i) => {
        text += `• ${highlight}\n`;
      });
    }
    
    text += `\n---\nGenerated by Whisprly`;
    
    try {
      const { Share } = await import('react-native');
      await Share.share({ message: text });
    } catch (error) {
      // Fallback to clipboard
      await Clipboard.setStringAsync(text);
      showToastMessage('Summary copied to clipboard!');
    }
  };

  // Copy summary to clipboard
  const copySummary = async () => {
    if (!meetingSummary) return;
    
    const modeConfig = MODES.find(m => m.id === selectedMode);
    let text = `${modeConfig?.label || 'Meeting'} Summary\n`;
    text += `Duration: ${formatDuration(sessionDuration)}\n\n`;
    
    text += `Summary:\n`;
    meetingSummary.summary_points.forEach((point, i) => {
      text += `${i + 1}. ${point}\n`;
    });
    
    if (meetingSummary.action_items.length > 0) {
      text += `\nAction Items:\n`;
      meetingSummary.action_items.forEach((item, i) => {
        text += `${i + 1}. ${item.task}`;
        if (item.owner) text += ` (Owner: ${item.owner})`;
        if (item.due_date) text += ` [Due: ${item.due_date}]`;
        text += `\n`;
      });
    }
    
    if (meetingSummary.key_highlights.length > 0) {
      text += `\nKey Highlights:\n`;
      meetingSummary.key_highlights.forEach((highlight, i) => {
        text += `• ${highlight}\n`;
      });
    }
    
    await Clipboard.setStringAsync(text);
    showToastMessage('Summary copied!');
  };

  // Reset session state
  const resetSession = () => {
    setSessionId('');
    setSuggestions([]);
    setDetectedQuestion(false);
    setQuestionContext(null);
    setConversationContext([]);
    setLiveTranscript('');
    setFullTranscript('');
    setSessionDuration(0);
    setRecordingState('idle');
    setMeetingSummary(null);
    setConversationHistory([]); // Clear conversation history
    if (sessionTimerRef.current) clearInterval(sessionTimerRef.current);
  };

  const transcribeAudio = async (audioUri: string): Promise<string> => {
    try {
      console.log('Transcribing audio from:', audioUri);
      
      // Read file as base64 directly (skip file exists check to avoid deprecated API)
      let base64Audio: string;
      try {
        base64Audio = await FileSystem.readAsStringAsync(audioUri, {
          encoding: 'base64',
        });
      } catch (readError) {
        console.log('Failed to read audio file:', readError);
        return '';
      }
      
      console.log('Base64 audio length:', base64Audio?.length || 0);
      
      if (!base64Audio || base64Audio.length < 1000) {
        console.log('Audio too short, skipping transcription. Length:', base64Audio?.length || 0);
        return '';
      }
      
      console.log('Sending audio to transcription API...');
      const transcribeResponse = await fetch(`${API_BASE_URL}/api/transcribe-base64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio: base64Audio, language: 'en' }),
      });
      
      const data = await transcribeResponse.json();
      console.log('Transcription response:', JSON.stringify(data));
      
      if (data.success && data.text) {
        return data.text.trim();
      } else if (data.error) {
        console.log('Transcription API error:', data.error);
      }
      return '';
    } catch (error) {
      console.error('Transcription error:', error);
      return '';
    }
  };

  // Recording Functions
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
    } catch (error) {
      console.error('Failed to start recording chunk:', error);
    }
  };

  // Web-specific recording functions
  const startWebRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      webStreamRef.current = stream;
      webAudioChunksRef.current = [];
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          webAudioChunksRef.current.push(event.data);
        }
      };
      
      webMediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      console.log('Web recording started');
    } catch (error) {
      console.error('Failed to start web recording:', error);
      throw error;
    }
  };

  const stopWebRecording = async (): Promise<string | null> => {
    return new Promise((resolve) => {
      if (!webMediaRecorderRef.current) {
        resolve(null);
        return;
      }
      
      webMediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(webAudioChunksRef.current, { type: 'audio/webm' });
        webAudioChunksRef.current = [];
        
        // Convert blob to base64
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve(base64);
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(audioBlob);
      };
      
      webMediaRecorderRef.current.stop();
    });
  };

  const cleanupWebRecording = () => {
    if (webStreamRef.current) {
      webStreamRef.current.getTracks().forEach(track => track.stop());
      webStreamRef.current = null;
    }
    webMediaRecorderRef.current = null;
    webAudioChunksRef.current = [];
  };

  // Transcribe audio from base64 (for web)
  const transcribeAudioBase64 = async (base64Audio: string): Promise<string> => {
    try {
      console.log('Transcribing web audio, base64 length:', base64Audio?.length || 0);
      
      if (!base64Audio || base64Audio.length < 1000) {
        console.log('Audio too short for transcription');
        return '';
      }
      
      const response = await fetch(`${API_BASE_URL}/api/transcribe-base64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio: base64Audio, language: 'en', format: 'webm' }),
      });
      
      const data = await response.json();
      console.log('Web transcription response:', data);
      
      if (data.success && data.text) {
        return data.text.trim();
      }
      return '';
    } catch (error) {
      console.error('Web transcription error:', error);
      return '';
    }
  };

  const processRecordingChunk = async () => {
    if (!isRecordingRef.current || isPausedRef.current) return;
    
    try {
      setRecordingState('processing');
      
      if (isWeb) {
        // Web browser processing
        const base64Audio = await stopWebRecording();
        
        // Start new recording immediately if still active
        if (isRecordingRef.current && !isPausedRef.current) {
          await startWebRecording();
          setRecordingState('recording');
        }
        
        // Process audio in background
        if (base64Audio) {
          const transcribedText = await transcribeAudioBase64(base64Audio);
          if (transcribedText && transcribedText.length > 0) {
            setLiveTranscript(transcribedText);
            const newFullTranscript = fullTranscript ? `${fullTranscript} ${transcribedText}` : transcribedText;
            setFullTranscript(newFullTranscript.slice(-500));
            
            const textForSuggestions = newFullTranscript.length > 50 ? newFullTranscript.slice(-200) : newFullTranscript;
            if (textForSuggestions.length >= 5) {
              await fetchSuggestions(textForSuggestions);
            }
          }
        }
      } else {
        // Mobile (Expo) processing
        if (recordingRef.current) {
          await recordingRef.current.stopAndUnloadAsync();
          const uri = recordingRef.current.getURI();
          recordingRef.current = null;
          
          // Start new recording immediately if still active
          if (isRecordingRef.current && !isPausedRef.current) {
            await startNewRecordingChunk();
            setRecordingState('recording');
          }
          
          // Process audio in background
          if (uri) {
            const transcribedText = await transcribeAudio(uri);
            if (transcribedText && transcribedText.length > 0) {
              setLiveTranscript(transcribedText);
              const newFullTranscript = fullTranscript ? `${fullTranscript} ${transcribedText}` : transcribedText;
              setFullTranscript(newFullTranscript.slice(-500));
              
              const textForSuggestions = newFullTranscript.length > 50 ? newFullTranscript.slice(-200) : newFullTranscript;
              if (textForSuggestions.length >= 5) {
                await fetchSuggestions(textForSuggestions);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error processing chunk:', error);
      if (isRecordingRef.current && !isPausedRef.current) {
        if (isWeb) {
          await startWebRecording();
        } else {
          await startNewRecordingChunk();
        }
        setRecordingState('recording');
      }
    }
  };

  // START Recording
  const handleStartRecording = async () => {
    try {
      if (isWeb) {
        // Web browser recording
        try {
          await startWebRecording();
        } catch (error) {
          Alert.alert('Microphone Access', 'Please allow microphone access in your browser to use this feature.');
          return;
        }
      } else {
        // Mobile recording
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert('Permission Required', 'Please grant microphone access.');
          return;
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });

        await startNewRecordingChunk();
      }

      isRecordingRef.current = true;
      isPausedRef.current = false;
      setRecordingState('recording');
      setLiveTranscript('Listening...');
      showToastMessage('Recording started!');
      
      // Set up interval for processing chunks
      recordingIntervalRef.current = setInterval(processRecordingChunk, RECORDING_INTERVAL);
    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Error', 'Failed to start recording. Please check microphone permissions.');
    }
  };

  // PAUSE Recording
  const handlePauseRecording = async () => {
    try {
      isPausedRef.current = true;
      setRecordingState('paused');
      
      if (isWeb) {
        // Stop web recording
        if (webMediaRecorderRef.current && webMediaRecorderRef.current.state === 'recording') {
          webMediaRecorderRef.current.pause();
        }
      } else {
        // Stop current mobile recording chunk
        if (recordingRef.current) {
          await recordingRef.current.stopAndUnloadAsync();
          recordingRef.current = null;
        }
      }
      
      // Clear interval
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
      
      showToastMessage('Recording paused');
    } catch (error) {
      console.error('Failed to pause recording:', error);
    }
  };

  // RESUME Recording
  const handleResumeRecording = async () => {
    try {
      isPausedRef.current = false;
      setRecordingState('recording');
      
      if (isWeb) {
        // Resume or start new web recording
        if (webMediaRecorderRef.current && webMediaRecorderRef.current.state === 'paused') {
          webMediaRecorderRef.current.resume();
        } else {
          await startWebRecording();
        }
      } else {
        // Start new mobile recording chunk
        await startNewRecordingChunk();
      }
      
      // Resume interval
      recordingIntervalRef.current = setInterval(processRecordingChunk, RECORDING_INTERVAL);
      
      showToastMessage('Recording resumed');
    } catch (error) {
      console.error('Failed to resume recording:', error);
    }
  };

  // STOP Recording
  const handleStopRecording = async () => {
    try {
      isRecordingRef.current = false;
      isPausedRef.current = false;
      
      // Clear interval
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
      
      if (isWeb) {
        // Stop web recording and cleanup
        if (webMediaRecorderRef.current && webMediaRecorderRef.current.state !== 'inactive') {
          webMediaRecorderRef.current.stop();
        }
        cleanupWebRecording();
      } else {
        // Stop mobile recording
        if (recordingRef.current) {
          await recordingRef.current.stopAndUnloadAsync();
          recordingRef.current = null;
        }
      }
      
      setRecordingState('idle');
      showToastMessage('Recording stopped');
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  // Other API functions
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
      setSavedSuggestions(await suggestionsRes.json());
      setNotes(await notesRes.json());
    } catch (error) {
      console.error('Failed to fetch session details:', error);
    }
  };

  const saveSuggestion = async (suggestion: Suggestion) => {
    try {
      await fetch(`${API_BASE_URL}/api/suggestions/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, text: suggestion.text, tone: suggestion.tone }),
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
      const url = editingNoteId ? `${API_BASE_URL}/api/notes/${editingNoteId}` : `${API_BASE_URL}/api/notes`;
      await fetch(url, {
        method: editingNoteId ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedHistorySession?.id || sessionId, text: noteText }),
      });
      setNoteText('');
      setEditingNoteId(null);
      setShowNoteModal(false);
      if (selectedHistorySession) fetchSessionDetails(selectedHistorySession.id);
      showToastMessage(editingNoteId ? 'Note updated!' : 'Note created!');
    } catch (error) {
      console.error('Failed to save note:', error);
    }
  };

  const deleteSession = async (deleteSessionId: string) => {
    try {
      await fetch(`${API_BASE_URL}/api/sessions/${deleteSessionId}`, { method: 'DELETE' });
      fetchSessionHistory();
      setCurrentScreen('history');
      showToastMessage('Session deleted');
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const deleteAllData = async () => {
    Alert.alert('Delete All Data', 'This will permanently delete all data.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete All',
        style: 'destructive',
        onPress: async () => {
          try {
            await fetch(`${API_BASE_URL}/api/sessions`, { method: 'DELETE' });
            fetchSessionHistory();
            showToastMessage('All data deleted');
          } catch (error) {}
        },
      },
    ]);
  };

  const handleSimulateInput = async () => {
    const sampleInputs = [
      "Can you tell me about your experience with project management?",
      "What makes your product different from competitors?",
      "How would you handle a difficult team member?",
      "What are your thoughts on the budget proposal?",
      "Could you walk me through your sales process?",
    ];
    const randomInput = sampleInputs[Math.floor(Math.random() * sampleInputs.length)];
    setLiveTranscript(randomInput);
    await fetchSuggestions(randomInput);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await Clipboard.setStringAsync(text);
      showToastMessage('Copied!');
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (error) {}
  };

  // Navigation
  const handleStartSession = async (mode: Mode) => {
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
    setRecordingState('idle'); // Don't auto-start recording!
    setCurrentScreen('session');
  };

  const handleEndSession = async () => {
    await handleStopRecording();
    try {
      await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration: sessionDuration }),
      });
    } catch (error) {}
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

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getModeConfig = (mode: string) => MODES.find((m) => m.id === mode) || MODES[3];

  // Render Toast
  const renderToast = () => {
    if (!showToast) return null;
    return (
      <View style={styles.toast}>
        <Ionicons name="checkmark-circle" size={18} color="#10B981" />
        <Text style={styles.toastText}>{toastMessage}</Text>
      </View>
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
          <TouchableOpacity style={styles.dangerButton} onPress={deleteAllData}>
            <Ionicons name="trash-outline" size={20} color="#EF4444" />
            <Text style={styles.dangerButtonText}>Delete All Data</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.preferencesButton} 
            onPress={() => { setShowSettingsModal(false); setShowPreferencesModal(true); }}
          >
            <Ionicons name="options-outline" size={20} color="#8B5CF6" />
            <Text style={styles.preferencesButtonText}>Response Preferences</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.knowledgeBaseButton} 
            onPress={() => { setShowSettingsModal(false); setCurrentScreen('knowledge'); }}
          >
            <Ionicons name="library-outline" size={20} color="#10B981" />
            <Text style={styles.knowledgeBaseButtonText}>Knowledge Base</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  // Render Response Preferences Modal
  const renderPreferencesModal = () => (
    <Modal visible={showPreferencesModal} transparent animationType="slide">
      <View style={styles.modalOverlay}>
        <ScrollView style={styles.preferencesModalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Response Preferences</Text>
            <TouchableOpacity onPress={() => setShowPreferencesModal(false)}>
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
          
          {/* Tone Selection */}
          <Text style={styles.prefSectionTitle}>Tone</Text>
          <View style={styles.prefOptionsRow}>
            {TONE_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.prefOption, preferences.tone === option.value && styles.prefOptionSelected]}
                onPress={() => savePreferences({ ...preferences, tone: option.value as any })}
              >
                <Ionicons name={option.icon as any} size={18} color={preferences.tone === option.value ? '#8B5CF6' : '#9CA3AF'} />
                <Text style={[styles.prefOptionText, preferences.tone === option.value && styles.prefOptionTextSelected]}>{option.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          
          {/* Style Selection */}
          <Text style={styles.prefSectionTitle}>Response Style</Text>
          <View style={styles.prefOptionsColumn}>
            {STYLE_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.prefOptionFull, preferences.style === option.value && styles.prefOptionSelected]}
                onPress={() => savePreferences({ ...preferences, style: option.value as any })}
              >
                <View style={[styles.prefRadio, preferences.style === option.value && styles.prefRadioSelected]} />
                <Text style={[styles.prefOptionText, preferences.style === option.value && styles.prefOptionTextSelected]}>{option.label}</Text>
                {option.value === 'star' && <Text style={styles.prefBadge}>Interview</Text>}
              </TouchableOpacity>
            ))}
          </View>
          
          {/* Risk Level */}
          <Text style={styles.prefSectionTitle}>Risk Tolerance</Text>
          <View style={styles.prefOptionsColumn}>
            {RISK_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.prefOptionFull, preferences.risk_level === option.value && styles.prefOptionSelected]}
                onPress={() => savePreferences({ ...preferences, risk_level: option.value as any })}
              >
                <View style={[styles.prefRadio, preferences.risk_level === option.value && styles.prefRadioSelected]} />
                <View style={styles.prefOptionContent}>
                  <Text style={[styles.prefOptionText, preferences.risk_level === option.value && styles.prefOptionTextSelected]}>{option.label}</Text>
                  <Text style={styles.prefOptionDesc}>{option.description}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
          
          {/* Interview-Specific Settings */}
          <Text style={styles.prefSectionTitle}>Interview Settings</Text>
          <Text style={styles.prefSubtitle}>Role Type</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.prefScrollRow}>
            {ROLE_OPTIONS.map((role) => (
              <TouchableOpacity
                key={role}
                style={[styles.prefChip, preferences.role_type === role && styles.prefChipSelected]}
                onPress={() => savePreferences({ ...preferences, role_type: preferences.role_type === role ? null : role })}
              >
                <Text style={[styles.prefChipText, preferences.role_type === role && styles.prefChipTextSelected]}>{role}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          
          <Text style={styles.prefSubtitle}>Seniority Level</Text>
          <View style={styles.prefOptionsRow}>
            {SENIORITY_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.prefOption, preferences.seniority_level === option.value && styles.prefOptionSelected]}
                onPress={() => savePreferences({ ...preferences, seniority_level: preferences.seniority_level === option.value ? null : option.value as any })}
              >
                <Text style={[styles.prefOptionText, preferences.seniority_level === option.value && styles.prefOptionTextSelected]}>{option.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          
          {/* Reset to Defaults */}
          <TouchableOpacity style={styles.resetButton} onPress={() => savePreferences(DEFAULT_PREFERENCES)}>
            <Ionicons name="refresh-outline" size={18} color="#9CA3AF" />
            <Text style={styles.resetButtonText}>Reset to Defaults</Text>
          </TouchableOpacity>
          
          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </Modal>
  );

  // Render Inactivity Prompt
  const renderInactivityPrompt = () => {
    if (!showInactivityPrompt) return null;
    return (
      <View style={styles.inactivityPrompt}>
        <Ionicons name="time-outline" size={20} color="#F59E0B" />
        <Text style={styles.inactivityText}>No activity for 60 seconds</Text>
        <TouchableOpacity style={styles.endMeetingPromptBtn} onPress={handleEndMeeting}>
          <Text style={styles.endMeetingPromptText}>End Meeting</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={resetInactivityTimer}>
          <Ionicons name="close" size={20} color="#9CA3AF" />
        </TouchableOpacity>
      </View>
    );
  };

  // Render Summary Screen
  const renderSummaryScreen = () => {
    const modeConfig = MODES.find(m => m.id === selectedMode);
    
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.header}>
          <TouchableOpacity onPress={() => { resetSession(); setCurrentScreen('home'); }} style={styles.backButton}>
            <Ionicons name="checkmark" size={24} color="#10B981" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Meeting Summary</Text>
            <View style={[styles.modeBadge, { backgroundColor: modeConfig?.color + '20' }]}>
              <Ionicons name={modeConfig?.icon || 'chatbubbles'} size={14} color={modeConfig?.color} />
              <Text style={[styles.modeBadgeText, { color: modeConfig?.color }]}>{modeConfig?.label}</Text>
            </View>
          </View>
          <View style={styles.headerRight}>
            <Text style={styles.durationText}>{formatDuration(sessionDuration)}</Text>
          </View>
        </View>
        
        <ScrollView style={styles.summaryContent} showsVerticalScrollIndicator={false}>
          {isGeneratingSummary ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#8B5CF6" />
              <Text style={styles.loadingText}>Generating summary...</Text>
            </View>
          ) : meetingSummary ? (
            <>
              {/* Summary Points */}
              <View style={styles.summarySection}>
                <View style={styles.summarySectionHeader}>
                  <Ionicons name="document-text-outline" size={20} color="#8B5CF6" />
                  <Text style={styles.summarySectionTitle}>Summary</Text>
                </View>
                {meetingSummary.summary_points.map((point, index) => (
                  <View key={index} style={styles.summaryPoint}>
                    <Text style={styles.summaryPointNumber}>{index + 1}.</Text>
                    <Text style={styles.summaryPointText}>{point}</Text>
                  </View>
                ))}
              </View>
              
              {/* Action Items */}
              {meetingSummary.action_items.length > 0 && (
                <View style={styles.summarySection}>
                  <View style={styles.summarySectionHeader}>
                    <Ionicons name="checkbox-outline" size={20} color="#10B981" />
                    <Text style={styles.summarySectionTitle}>Action Items</Text>
                  </View>
                  {meetingSummary.action_items.map((item, index) => (
                    <View key={index} style={styles.actionItem}>
                      <View style={styles.actionItemHeader}>
                        <Ionicons name="square-outline" size={18} color="#6B7280" />
                        <Text style={styles.actionItemTask}>{item.task}</Text>
                      </View>
                      <View style={styles.actionItemMeta}>
                        {item.owner && (
                          <View style={styles.actionItemTag}>
                            <Ionicons name="person-outline" size={12} color="#8B5CF6" />
                            <Text style={styles.actionItemTagText}>{item.owner}</Text>
                          </View>
                        )}
                        {item.due_date && (
                          <View style={styles.actionItemTag}>
                            <Ionicons name="calendar-outline" size={12} color="#F59E0B" />
                            <Text style={styles.actionItemTagText}>{item.due_date}</Text>
                          </View>
                        )}
                      </View>
                    </View>
                  ))}
                </View>
              )}
              
              {/* Key Highlights */}
              {meetingSummary.key_highlights.length > 0 && (
                <View style={styles.summarySection}>
                  <View style={styles.summarySectionHeader}>
                    <Ionicons name="flash-outline" size={20} color="#F59E0B" />
                    <Text style={styles.summarySectionTitle}>Key Highlights</Text>
                  </View>
                  {meetingSummary.key_highlights.map((highlight, index) => (
                    <View key={index} style={styles.highlightItem}>
                      <Text style={styles.highlightBullet}>•</Text>
                      <Text style={styles.highlightText}>{highlight}</Text>
                    </View>
                  ))}
                </View>
              )}
              
              {/* Share/Copy Buttons */}
              <View style={styles.summaryActions}>
                <TouchableOpacity style={styles.summaryActionBtn} onPress={copySummary}>
                  <Ionicons name="copy-outline" size={20} color="#FFFFFF" />
                  <Text style={styles.summaryActionText}>Copy</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.summaryActionBtn, styles.summaryShareBtn]} onPress={shareSummary}>
                  <Ionicons name="share-outline" size={20} color="#FFFFFF" />
                  <Text style={styles.summaryActionText}>Share</Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <View style={styles.emptySummary}>
              <Ionicons name="document-text-outline" size={48} color="#4B5563" />
              <Text style={styles.emptySummaryText}>No summary available</Text>
            </View>
          )}
        </ScrollView>
        
        <TouchableOpacity style={styles.doneButton} onPress={() => { resetSession(); setCurrentScreen('home'); }}>
          <Text style={styles.doneButtonText}>Done</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  };

  // Render Note Modal
  const renderNoteModal = () => (
    <Modal visible={showNoteModal} transparent animationType="slide">
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{editingNoteId ? 'Edit Note' : 'New Note'}</Text>
            <TouchableOpacity onPress={() => { setShowNoteModal(false); setNoteText(''); setEditingNoteId(null); }}>
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
          <TextInput style={styles.noteInput} placeholder="Write your note..." placeholderTextColor="#6B7280" multiline value={noteText} onChangeText={setNoteText} />
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
      <View style={styles.modesContainer}>
        <Text style={styles.sectionTitle}>Select Mode</Text>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.modesScrollContent}>
          {MODES.map((mode) => (
            <TouchableOpacity key={mode.id} style={[styles.modeCard, { borderColor: mode.color }]} onPress={() => handleStartSession(mode.id)} activeOpacity={0.7}>
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
      <View style={styles.homeFooter}>
        <Text style={styles.footerText}>Tap a mode to start</Text>
      </View>
      {renderSettingsModal()}
      {renderPreferencesModal()}
      {renderToast()}
    </SafeAreaView>
  );

  // Render Session Screen
  const renderSessionScreen = () => {
    const modeConfig = getModeConfig(selectedMode);
    const isRecording = recordingState === 'recording';
    const isPaused = recordingState === 'paused';
    const isProcessing = recordingState === 'processing';
    const isIdle = recordingState === 'idle';

    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.sessionHeader}>
          <TouchableOpacity onPress={() => {
            Alert.alert('End Session', 'Do you want to end this session?', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Just Exit', onPress: handleEndSession },
              { text: 'End & Summarize', onPress: handleEndMeeting, style: 'default' },
            ]);
          }} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
          </TouchableOpacity>
          <View style={styles.sessionHeaderCenter}>
            <View style={[styles.modeBadge, { backgroundColor: `${modeConfig.color}20` }]}>
              <Ionicons name={modeConfig.icon} size={16} color={modeConfig.color} />
              <Text style={[styles.modeBadgeText, { color: modeConfig.color }]}>{modeConfig.label}</Text>
            </View>
            <Text style={styles.durationText}>{formatDuration(sessionDuration)}</Text>
          </View>
          <TouchableOpacity style={styles.endMeetingBtn} onPress={handleEndMeeting}>
            <Text style={styles.endMeetingText}>End</Text>
          </TouchableOpacity>
        </View>

        {/* Recording Status */}
        {(isRecording || isPaused || isProcessing) && (
          <View style={[styles.statusBar, isRecording ? styles.statusBarRecording : isPaused ? styles.statusBarPaused : styles.statusBarProcessing]}>
            <View style={[styles.statusDot, isRecording ? styles.statusDotRecording : isPaused ? styles.statusDotPaused : styles.statusDotProcessing]} />
            <Text style={styles.statusText}>
              {isRecording ? 'Listening to meeting...' : isPaused ? 'Paused' : 'Processing audio...'}
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
            <Text style={styles.questionAlertText}>{questionContext}</Text>
          </View>
        )}

        {/* Conversation History - Scrollable List */}
        <ScrollView 
          ref={scrollViewRef}
          style={styles.suggestionsContainer} 
          contentContainerStyle={styles.suggestionsContent} 
          showsVerticalScrollIndicator={true}
        >
          {isLoading && conversationHistory.length === 0 ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#8B5CF6" />
              <Text style={styles.loadingText}>Generating suggestions...</Text>
            </View>
          ) : conversationHistory.length > 0 ? (
            <View>
              <View style={styles.conversationHistoryHeader}>
                <Text style={styles.suggestionsTitle}>Conversation History</Text>
                <Text style={styles.historyCount}>{conversationHistory.length} entries</Text>
              </View>
              
              {/* Display all conversation entries */}
              {conversationHistory.map((entry, entryIndex) => (
                <View key={entry.id} style={styles.conversationEntry}>
                  {/* Timestamp and transcript */}
                  <View style={styles.entryHeader}>
                    <Text style={styles.entryNumber}>#{entryIndex + 1}</Text>
                    <Text style={styles.entryTime}>
                      {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Text>
                  </View>
                  
                  {/* Detected Question */}
                  {entry.question && (
                    <View style={styles.entryQuestion}>
                      <Ionicons name="help-circle-outline" size={14} color="#F59E0B" />
                      <Text style={styles.entryQuestionText}>{entry.question}</Text>
                    </View>
                  )}
                  
                  {/* Transcript snippet */}
                  <Text style={styles.entryTranscript} numberOfLines={2}>
                    "{entry.transcript}"
                  </Text>
                  
                  {/* Suggestions for this entry */}
                  {entry.suggestions.map((suggestion, sugIndex) => (
                    <View key={sugIndex} style={styles.suggestionCard}>
                      <View style={styles.suggestionHeader}>
                        <View style={styles.priorityBadge}><Text style={styles.priorityText}>#{suggestion.priority}</Text></View>
                        <View style={styles.toneBadge}><Text style={styles.toneText}>{suggestion.tone}</Text></View>
                      </View>
                      <Text style={styles.suggestionText}>{suggestion.text}</Text>
                      <View style={styles.suggestionActions}>
                        <TouchableOpacity style={styles.actionButton} onPress={() => copyToClipboard(suggestion.text)}>
                          <Ionicons name="copy-outline" size={18} color="#8B5CF6" />
                          <Text style={styles.actionButtonText}>Copy</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.actionButton} onPress={() => saveSuggestion(suggestion)}>
                          <Ionicons name="bookmark-outline" size={18} color="#10B981" />
                          <Text style={[styles.actionButtonText, { color: '#10B981' }]}>Save</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))}
                </View>
              ))}
              
              {/* Loading indicator for new suggestions */}
              {isLoading && (
                <View style={styles.loadingMore}>
                  <ActivityIndicator size="small" color="#8B5CF6" />
                  <Text style={styles.loadingMoreText}>Getting new suggestions...</Text>
                </View>
              )}
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="mic-outline" size={56} color="#4B5563" />
              <Text style={styles.emptyStateTitle}>Ready to assist</Text>
              <Text style={styles.emptyStateText}>Tap the microphone button to start{'\n'}listening to your meeting</Text>
              <View style={styles.instructionBox}>
                <Text style={styles.instructionTitle}>How it works:</Text>
                <Text style={styles.instructionText}>1. Tap the mic to start listening</Text>
                <Text style={styles.instructionText}>2. The app will hear your meeting</Text>
                <Text style={styles.instructionText}>3. Get instant response suggestions</Text>
                <Text style={styles.instructionText}>4. Scroll up to see previous answers</Text>
              </View>
            </View>
          )}
        </ScrollView>

        {/* Control Buttons */}
        <View style={styles.controlsContainer}>
          {/* Test Button */}
          <TouchableOpacity style={styles.testButton} onPress={handleSimulateInput} activeOpacity={0.7}>
            <Ionicons name="flash-outline" size={20} color="#6B7280" />
            <Text style={styles.testButtonText}>Test</Text>
          </TouchableOpacity>

          {/* Main Recording Controls */}
          <View style={styles.recordingControls}>
            {isIdle ? (
              // START button
              <TouchableOpacity style={[styles.mainButton, { backgroundColor: modeConfig.color }]} onPress={handleStartRecording} activeOpacity={0.7}>
                <Ionicons name="mic" size={32} color="#FFFFFF" />
              </TouchableOpacity>
            ) : (
              // PAUSE/RESUME and STOP buttons
              <View style={styles.activeControls}>
                {/* Pause/Resume Button */}
                <TouchableOpacity
                  style={[styles.controlButton, isPaused ? styles.resumeButton : styles.pauseButton]}
                  onPress={isPaused ? handleResumeRecording : handlePauseRecording}
                  activeOpacity={0.7}
                >
                  <Ionicons name={isPaused ? 'play' : 'pause'} size={24} color="#FFFFFF" />
                </TouchableOpacity>

                {/* Recording indicator */}
                <View style={styles.recordingIndicator}>
                  <View style={[styles.recordingDot, isRecording && styles.recordingDotActive]} />
                </View>

                {/* Stop Button */}
                <TouchableOpacity style={[styles.controlButton, styles.stopButton]} onPress={handleStopRecording} activeOpacity={0.7}>
                  <Ionicons name="stop" size={24} color="#FFFFFF" />
                </TouchableOpacity>
              </View>
            )}
          </View>
        </View>

        {/* Bottom Hint */}
        <View style={styles.bottomHint}>
          <Text style={styles.bottomHintText}>
            {isIdle ? 'Tap the mic to start listening' : isRecording ? 'Listening... tap pause or stop' : isPaused ? 'Paused - tap play to resume' : 'Processing...'}
          </Text>
        </View>

        {renderInactivityPrompt()}
        {renderToast()}
        {renderPreferencesModal()}
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
          </View>
        ) : (
          sessionHistoryList.map((session) => {
            const modeConfig = getModeConfig(session.mode);
            return (
              <TouchableOpacity key={session.id} style={styles.historyCard} onPress={() => handleViewSessionDetail(session)}>
                <View style={[styles.historyModeIcon, { backgroundColor: `${modeConfig.color}20` }]}>
                  <Ionicons name={modeConfig.icon} size={24} color={modeConfig.color} />
                </View>
                <View style={styles.historyCardContent}>
                  <Text style={styles.historyCardTitle}>{modeConfig.label}</Text>
                  <Text style={styles.historyCardDate}>{formatDate(session.created_at)}</Text>
                  <View style={styles.historyCardStats}>
                    <View style={styles.statItem}><Ionicons name="bookmark" size={14} color="#6B7280" /><Text style={styles.statText}>{session.saved_suggestions_count}</Text></View>
                    <View style={styles.statItem}><Ionicons name="time" size={14} color="#6B7280" /><Text style={styles.statText}>{formatDuration(session.duration)}</Text></View>
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
                    <View style={styles.toneBadge}><Text style={styles.toneText}>{suggestion.tone}</Text></View>
                    <TouchableOpacity onPress={() => copyToClipboard(suggestion.text)}><Ionicons name="copy-outline" size={18} color="#8B5CF6" /></TouchableOpacity>
                  </View>
                  <Text style={styles.savedSuggestionText}>{suggestion.text}</Text>
                </View>
              ))
            )}
          </View>
          <View style={styles.detailSection}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionHeaderText}>Notes</Text>
              <TouchableOpacity onPress={() => setShowNoteModal(true)}><Ionicons name="add-circle" size={24} color="#8B5CF6" /></TouchableOpacity>
            </View>
            {notes.length === 0 ? (
              <Text style={styles.noItemsText}>No notes yet</Text>
            ) : (
              notes.map((note) => (
                <View key={note.id} style={styles.noteCard}>
                  <Text style={styles.noteText}>{note.text}</Text>
                  <TouchableOpacity onPress={() => { setNoteText(note.text); setEditingNoteId(note.id); setShowNoteModal(true); }}>
                    <Ionicons name="pencil-outline" size={18} color="#6B7280" />
                  </TouchableOpacity>
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

  // Render Knowledge Base Screen
  const renderKnowledgeBaseScreen = () => (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setCurrentScreen('home')} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Knowledge Base</Text>
        </View>
        <View style={styles.headerRight} />
      </View>

      <ScrollView style={styles.kbContent} contentContainerStyle={styles.kbContentContainer}>
        {/* Documents Section */}
        <View style={styles.kbSection}>
          <View style={styles.kbSectionHeader}>
            <View style={styles.kbSectionTitleRow}>
              <Ionicons name="document-text-outline" size={22} color="#8B5CF6" />
              <Text style={styles.kbSectionTitle}>Documents</Text>
              <Text style={styles.kbCount}>{knowledgeDocuments.length}</Text>
            </View>
            <TouchableOpacity 
              style={styles.kbAddButton} 
              onPress={() => {
                Alert.alert('Upload Document', 'Choose storage type:', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Session Only', onPress: () => uploadDocument('session') },
                  { text: 'Permanent', onPress: () => uploadDocument('persistent') },
                ]);
              }}
              disabled={isUploadingDoc}
            >
              {isUploadingDoc ? (
                <ActivityIndicator size="small" color="#8B5CF6" />
              ) : (
                <>
                  <Ionicons name="add" size={18} color="#8B5CF6" />
                  <Text style={styles.kbAddButtonText}>Add</Text>
                </>
              )}
            </TouchableOpacity>
          </View>

          {knowledgeDocuments.length === 0 ? (
            <View style={styles.kbEmpty}>
              <Ionicons name="cloud-upload-outline" size={40} color="#4B5563" />
              <Text style={styles.kbEmptyText}>No documents yet</Text>
              <Text style={styles.kbEmptySubtext}>Upload PDF, Word, Excel, or PowerPoint</Text>
            </View>
          ) : (
            knowledgeDocuments.map((doc) => (
              <View key={doc.id} style={styles.kbItem}>
                <View style={styles.kbItemIcon}>
                  <Ionicons 
                    name={
                      doc.file_type === 'pdf' ? 'document' :
                      doc.file_type === 'docx' ? 'document-text' :
                      doc.file_type === 'xlsx' ? 'grid' :
                      doc.file_type === 'pptx' ? 'easel' : 'document-outline'
                    } 
                    size={24} 
                    color="#8B5CF6" 
                  />
                </View>
                <View style={styles.kbItemContent}>
                  <Text style={styles.kbItemName} numberOfLines={1}>{doc.name}</Text>
                  <Text style={styles.kbItemMeta}>
                    {doc.file_type.toUpperCase()} • {(doc.file_size / 1024).toFixed(1)}KB • {doc.storage_type === 'session' ? '📌 Session' : '💾 Saved'}
                  </Text>
                  <Text style={styles.kbItemPreview} numberOfLines={2}>{doc.content_preview}</Text>
                </View>
                <TouchableOpacity onPress={() => deleteDocument(doc.id)} style={styles.kbDeleteButton}>
                  <Ionicons name="trash-outline" size={20} color="#EF4444" />
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        {/* Notes Section */}
        <View style={styles.kbSection}>
          <View style={styles.kbSectionHeader}>
            <View style={styles.kbSectionTitleRow}>
              <Ionicons name="create-outline" size={22} color="#10B981" />
              <Text style={styles.kbSectionTitle}>Notes</Text>
              <Text style={styles.kbCount}>{knowledgeNotes.length}</Text>
            </View>
            <TouchableOpacity style={styles.kbAddButton} onPress={() => setShowAddNoteModal(true)}>
              <Ionicons name="add" size={18} color="#10B981" />
              <Text style={[styles.kbAddButtonText, { color: '#10B981' }]}>Add</Text>
            </TouchableOpacity>
          </View>

          {knowledgeNotes.length === 0 ? (
            <View style={styles.kbEmpty}>
              <Ionicons name="pencil-outline" size={40} color="#4B5563" />
              <Text style={styles.kbEmptyText}>No notes yet</Text>
              <Text style={styles.kbEmptySubtext}>Add notes for quick reference</Text>
            </View>
          ) : (
            knowledgeNotes.map((note) => (
              <View key={note.id} style={styles.kbItem}>
                <View style={[styles.kbItemIcon, { backgroundColor: '#10B98120' }]}>
                  <Ionicons name="document-text" size={24} color="#10B981" />
                </View>
                <View style={styles.kbItemContent}>
                  <Text style={styles.kbItemName}>{note.title}</Text>
                  <Text style={styles.kbItemMeta}>{note.storage_type === 'session' ? '📌 Session' : '💾 Saved'}</Text>
                  <Text style={styles.kbItemPreview} numberOfLines={2}>{note.content_preview}</Text>
                </View>
                <TouchableOpacity onPress={() => deleteNote(note.id)} style={styles.kbDeleteButton}>
                  <Ionicons name="trash-outline" size={20} color="#EF4444" />
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        {/* Info Box */}
        <View style={styles.kbInfoBox}>
          <Ionicons name="information-circle-outline" size={20} color="#6B7280" />
          <Text style={styles.kbInfoText}>
            Documents and notes are used by the AI to provide more accurate and contextual suggestions during your meetings and interviews.
          </Text>
        </View>
      </ScrollView>

      {/* Add Note Modal */}
      <Modal visible={showAddNoteModal} transparent animationType="slide">
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalOverlay}>
          <View style={styles.addNoteModal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Note</Text>
              <TouchableOpacity onPress={() => setShowAddNoteModal(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.noteInput}
              placeholder="Note title"
              placeholderTextColor="#6B7280"
              value={newNoteTitle}
              onChangeText={setNewNoteTitle}
            />

            <TextInput
              style={[styles.noteInput, styles.noteContentInput]}
              placeholder="Note content (e.g., key talking points, company info, product details)"
              placeholderTextColor="#6B7280"
              value={newNoteContent}
              onChangeText={setNewNoteContent}
              multiline
              numberOfLines={6}
              textAlignVertical="top"
            />

            <View style={styles.storageTypeRow}>
              <Text style={styles.storageTypeLabel}>Storage:</Text>
              <TouchableOpacity 
                style={[styles.storageTypeOption, newNoteStorageType === 'persistent' && styles.storageTypeSelected]}
                onPress={() => setNewNoteStorageType('persistent')}
              >
                <Text style={[styles.storageTypeText, newNoteStorageType === 'persistent' && styles.storageTypeTextSelected]}>💾 Permanent</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.storageTypeOption, newNoteStorageType === 'session' && styles.storageTypeSelected]}
                onPress={() => setNewNoteStorageType('session')}
              >
                <Text style={[styles.storageTypeText, newNoteStorageType === 'session' && styles.storageTypeTextSelected]}>📌 Session</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.saveNoteButton} onPress={addNote}>
              <Text style={styles.saveNoteButtonText}>Save Note</Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {renderToast()}
    </SafeAreaView>
  );

  // Main render
  switch (currentScreen) {
    case 'session': return renderSessionScreen();
    case 'history': return renderHistoryScreen();
    case 'sessionDetail': return renderSessionDetailScreen();
    case 'summary': return renderSummaryScreen();
    case 'knowledge': return renderKnowledgeBaseScreen();
    default: return renderHomeScreen();
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F0F14' },
  
  // Home
  homeHeader: { alignItems: 'center', paddingTop: Platform.OS === 'android' ? 40 : 20, paddingBottom: 24 },
  logoContainer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  logoText: { fontSize: 32, fontWeight: '700', color: '#FFFFFF', letterSpacing: -1 },
  tagline: { fontSize: 14, color: '#6B7280', marginTop: 8 },
  headerActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  headerButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#1A1A24', alignItems: 'center', justifyContent: 'center' },
  modesContainer: { flex: 1, paddingHorizontal: 20 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#FFFFFF', marginBottom: 16 },
  modesScrollContent: { paddingBottom: 20 },
  modeCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1A24', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1 },
  modeIconContainer: { width: 52, height: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  modeTextContainer: { flex: 1, marginLeft: 14 },
  modeLabel: { fontSize: 17, fontWeight: '600', color: '#FFFFFF', marginBottom: 4 },
  modeDescription: { fontSize: 13, color: '#9CA3AF', lineHeight: 18 },
  homeFooter: { alignItems: 'center', paddingVertical: 20 },
  footerText: { fontSize: 13, color: '#6B7280' },

  // Session
  sessionHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: Platform.OS === 'android' ? 40 : 12, paddingBottom: 12 },
  backButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  sessionHeaderCenter: { flex: 1, alignItems: 'center' },
  headerSpacer: { width: 44 },
  modeBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, gap: 6 },
  modeBadgeText: { fontSize: 14, fontWeight: '600' },
  durationText: { fontSize: 12, color: '#6B7280', marginTop: 4 },

  // Status Bar
  statusBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginHorizontal: 16, padding: 10, borderRadius: 12, marginBottom: 8, gap: 8 },
  statusBarRecording: { backgroundColor: '#10B98120' },
  statusBarPaused: { backgroundColor: '#F59E0B20' },
  statusBarProcessing: { backgroundColor: '#6366F120' },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusDotRecording: { backgroundColor: '#10B981' },
  statusDotPaused: { backgroundColor: '#F59E0B' },
  statusDotProcessing: { backgroundColor: '#6366F1' },
  statusText: { fontSize: 14, fontWeight: '600', color: '#FFFFFF' },

  transcriptBox: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#1A1A24', marginHorizontal: 16, padding: 12, borderRadius: 12, gap: 8, marginBottom: 8 },
  transcriptText: { flex: 1, color: '#D1D5DB', fontSize: 14, lineHeight: 20 },
  questionAlert: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FEF3C7', marginHorizontal: 16, padding: 12, borderRadius: 12, gap: 8, marginBottom: 8 },
  questionAlertText: { flex: 1, fontSize: 13, color: '#92400E', fontWeight: '500' },

  suggestionsContainer: { flex: 1 },
  suggestionsContent: { padding: 16 },
  suggestionsTitle: { fontSize: 16, fontWeight: '600', color: '#FFFFFF', marginBottom: 12 },
  loadingContainer: { alignItems: 'center', paddingVertical: 60 },
  loadingText: { color: '#9CA3AF', marginTop: 12, fontSize: 14 },

  suggestionCard: { backgroundColor: '#1A1A24', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#2D2D3A' },
  suggestionHeader: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  priorityBadge: { backgroundColor: '#8B5CF620', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  priorityText: { color: '#8B5CF6', fontSize: 12, fontWeight: '700' },
  toneBadge: { backgroundColor: '#374151', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  toneText: { color: '#D1D5DB', fontSize: 12, fontWeight: '500', textTransform: 'capitalize' },
  suggestionText: { color: '#FFFFFF', fontSize: 16, lineHeight: 24, marginBottom: 12 },
  suggestionActions: { flexDirection: 'row', gap: 16, borderTopWidth: 1, borderTopColor: '#2D2D3A', paddingTop: 12 },
  actionButton: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  actionButtonText: { color: '#8B5CF6', fontSize: 13, fontWeight: '500' },

  emptyState: { alignItems: 'center', paddingVertical: 40 },
  emptyStateTitle: { color: '#FFFFFF', fontSize: 20, fontWeight: '600', marginTop: 16 },
  emptyStateText: { color: '#6B7280', fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 22 },
  instructionBox: { backgroundColor: '#1A1A24', borderRadius: 12, padding: 16, marginTop: 24, width: '100%' },
  instructionTitle: { color: '#FFFFFF', fontSize: 14, fontWeight: '600', marginBottom: 12 },
  instructionText: { color: '#9CA3AF', fontSize: 13, marginBottom: 6 },

  // Controls
  controlsContainer: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, gap: 12, borderTopWidth: 1, borderTopColor: '#2D2D3A' },
  testButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1A24', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, gap: 8 },
  testButtonText: { color: '#6B7280', fontSize: 14 },
  recordingControls: { flex: 1, alignItems: 'center' },
  mainButton: { width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center', elevation: 4 },
  activeControls: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 16 },
  controlButton: { width: 50, height: 50, borderRadius: 25, alignItems: 'center', justifyContent: 'center' },
  pauseButton: { backgroundColor: '#F59E0B' },
  resumeButton: { backgroundColor: '#10B981' },
  stopButton: { backgroundColor: '#EF4444' },
  recordingIndicator: { width: 20, height: 20, alignItems: 'center', justifyContent: 'center' },
  recordingDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: '#374151' },
  recordingDotActive: { backgroundColor: '#EF4444' },

  bottomHint: { alignItems: 'center', paddingBottom: 16 },
  bottomHintText: { color: '#6B7280', fontSize: 12 },

  // Toast
  toast: { position: 'absolute', bottom: 140, alignSelf: 'center', flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1A24', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, gap: 8, borderWidth: 1, borderColor: '#10B98140' },
  toastText: { color: '#FFFFFF', fontSize: 14, fontWeight: '500' },

  // History
  historyHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: Platform.OS === 'android' ? 40 : 12, paddingBottom: 16 },
  historyTitle: { flex: 1, fontSize: 20, fontWeight: '600', color: '#FFFFFF', textAlign: 'center' },
  historyList: { flex: 1 },
  historyListContent: { padding: 16 },
  emptyHistory: { alignItems: 'center', paddingVertical: 60 },
  emptyHistoryText: { color: '#FFFFFF', fontSize: 18, fontWeight: '600', marginTop: 16 },
  historyCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1A24', borderRadius: 14, padding: 14, marginBottom: 10 },
  historyModeIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  historyCardContent: { flex: 1, marginLeft: 12 },
  historyCardTitle: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  historyCardDate: { color: '#6B7280', fontSize: 12, marginTop: 2 },
  historyCardStats: { flexDirection: 'row', gap: 12, marginTop: 6 },
  statItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statText: { color: '#6B7280', fontSize: 12 },

  // Session Detail
  sessionDetailTitle: { flex: 1, alignItems: 'center' },
  sessionDetailDate: { color: '#6B7280', fontSize: 12, marginTop: 2 },
  detailContent: { flex: 1, padding: 16 },
  detailSection: { marginBottom: 24 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  sectionHeaderText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  sectionCount: { color: '#6B7280', fontSize: 14 },
  noItemsText: { color: '#6B7280', fontSize: 14, fontStyle: 'italic' },
  savedSuggestionCard: { backgroundColor: '#1A1A24', borderRadius: 12, padding: 14, marginBottom: 8 },
  savedSuggestionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  savedSuggestionText: { color: '#D1D5DB', fontSize: 14, lineHeight: 20 },
  noteCard: { backgroundColor: '#1A1A24', borderRadius: 12, padding: 14, marginBottom: 8, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  noteText: { color: '#D1D5DB', fontSize: 14, lineHeight: 20, flex: 1 },

  // Knowledge Base Styles
  kbContent: { flex: 1 },
  kbContentContainer: { padding: 16 },
  kbSection: { marginBottom: 24 },
  kbSectionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  kbSectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  kbSectionTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '700' },
  kbCount: { backgroundColor: '#2D2D3A', color: '#9CA3AF', fontSize: 12, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  kbAddButton: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#2D2D3A', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 8 },
  kbAddButtonText: { color: '#8B5CF6', fontSize: 14, fontWeight: '600' },
  kbEmpty: { alignItems: 'center', padding: 32, backgroundColor: '#1A1A24', borderRadius: 12, borderWidth: 1, borderColor: '#2D2D3A', borderStyle: 'dashed' },
  kbEmptyText: { color: '#6B7280', fontSize: 15, marginTop: 12 },
  kbEmptySubtext: { color: '#4B5563', fontSize: 13, marginTop: 4 },
  kbItem: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#1A1A24', borderRadius: 12, padding: 12, marginBottom: 10 },
  kbItemIcon: { width: 44, height: 44, borderRadius: 10, backgroundColor: '#8B5CF620', alignItems: 'center', justifyContent: 'center' },
  kbItemContent: { flex: 1, marginLeft: 12 },
  kbItemName: { color: '#FFFFFF', fontSize: 15, fontWeight: '600' },
  kbItemMeta: { color: '#6B7280', fontSize: 12, marginTop: 2 },
  kbItemPreview: { color: '#9CA3AF', fontSize: 13, marginTop: 6, lineHeight: 18 },
  kbDeleteButton: { padding: 8 },
  kbInfoBox: { flexDirection: 'row', gap: 10, backgroundColor: '#1A1A24', borderRadius: 12, padding: 14, marginTop: 8 },
  kbInfoText: { flex: 1, color: '#6B7280', fontSize: 13, lineHeight: 18 },
  
  // Add Note Modal
  addNoteModal: { backgroundColor: '#1A1A2E', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, maxHeight: '80%' },
  noteInput: { backgroundColor: '#2D2D3A', borderRadius: 12, padding: 14, color: '#FFFFFF', fontSize: 15, marginBottom: 12 },
  noteContentInput: { minHeight: 150, textAlignVertical: 'top' },
  storageTypeRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16 },
  storageTypeLabel: { color: '#9CA3AF', fontSize: 14 },
  storageTypeOption: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8, backgroundColor: '#2D2D3A' },
  storageTypeSelected: { backgroundColor: '#8B5CF620', borderWidth: 1, borderColor: '#8B5CF6' },
  storageTypeText: { color: '#9CA3AF', fontSize: 13 },
  storageTypeTextSelected: { color: '#8B5CF6' },
  saveNoteButton: { backgroundColor: '#10B981', paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  saveNoteButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  
  // Knowledge Base Button in Settings
  knowledgeBaseButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12, paddingVertical: 14, borderRadius: 12, backgroundColor: '#10B98110', borderWidth: 1, borderColor: '#10B981' },
  knowledgeBaseButtonText: { color: '#10B981', fontSize: 15, fontWeight: '600' },

  // Conversation History Styles
  conversationHistoryHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  historyCount: { color: '#6B7280', fontSize: 12 },
  conversationEntry: { backgroundColor: '#1A1A24', borderRadius: 14, padding: 14, marginBottom: 16, borderLeftWidth: 3, borderLeftColor: '#8B5CF6' },
  entryHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  entryNumber: { color: '#8B5CF6', fontSize: 12, fontWeight: '700' },
  entryTime: { color: '#6B7280', fontSize: 11 },
  entryQuestion: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#F59E0B10', borderRadius: 8, padding: 8, marginBottom: 10 },
  entryQuestionText: { color: '#F59E0B', fontSize: 13, flex: 1 },
  entryTranscript: { color: '#9CA3AF', fontSize: 12, fontStyle: 'italic', marginBottom: 12, lineHeight: 18 },
  loadingMore: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 16 },
  loadingMoreText: { color: '#6B7280', fontSize: 13 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#1A1A24', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: Platform.OS === 'ios' ? 40 : 20 },
  modalHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 },
  modalTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '600' },
  noteInput: { backgroundColor: '#0F0F14', borderRadius: 12, padding: 14, color: '#FFFFFF', fontSize: 15, minHeight: 120, textAlignVertical: 'top' },
  saveButton: { backgroundColor: '#8B5CF6', borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 16 },
  saveButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#2D2D3A' },
  settingInfo: { flexDirection: 'row', alignItems: 'center', flex: 1, gap: 12 },
  settingTextContainer: { flex: 1 },
  settingLabel: { color: '#FFFFFF', fontSize: 15, fontWeight: '500' },
  settingDescription: { color: '#6B7280', fontSize: 12, marginTop: 2 },
  dangerButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 24, paddingVertical: 14, borderRadius: 12, borderWidth: 1, borderColor: '#EF4444' },
  dangerButtonText: { color: '#EF4444', fontSize: 15, fontWeight: '600' },
  
  // Preferences Button in Settings
  preferencesButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 16, paddingVertical: 14, borderRadius: 12, backgroundColor: '#8B5CF610', borderWidth: 1, borderColor: '#8B5CF6' },
  preferencesButtonText: { color: '#8B5CF6', fontSize: 15, fontWeight: '600' },
  
  // Preferences Modal Styles
  preferencesModalContent: { flex: 1, backgroundColor: '#1A1A2E', marginTop: 60, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20 },
  prefSectionTitle: { color: '#FFFFFF', fontSize: 17, fontWeight: '700', marginTop: 20, marginBottom: 12 },
  prefSubtitle: { color: '#9CA3AF', fontSize: 14, fontWeight: '500', marginTop: 12, marginBottom: 8 },
  prefOptionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  prefOptionsColumn: { gap: 8 },
  prefOption: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 10, paddingHorizontal: 14, borderRadius: 20, backgroundColor: '#2D2D3A', borderWidth: 1, borderColor: 'transparent' },
  prefOptionSelected: { backgroundColor: '#8B5CF615', borderColor: '#8B5CF6' },
  prefOptionText: { color: '#9CA3AF', fontSize: 14 },
  prefOptionTextSelected: { color: '#8B5CF6', fontWeight: '600' },
  prefOptionFull: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, paddingHorizontal: 16, borderRadius: 12, backgroundColor: '#2D2D3A', borderWidth: 1, borderColor: 'transparent' },
  prefRadio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#6B7280' },
  prefRadioSelected: { borderColor: '#8B5CF6', backgroundColor: '#8B5CF6' },
  prefOptionContent: { flex: 1 },
  prefOptionDesc: { color: '#6B7280', fontSize: 12, marginTop: 2 },
  prefBadge: { fontSize: 10, color: '#F59E0B', backgroundColor: '#F59E0B20', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, marginLeft: 8 },
  prefScrollRow: { marginBottom: 8 },
  prefChip: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 16, backgroundColor: '#2D2D3A', marginRight: 8, borderWidth: 1, borderColor: 'transparent' },
  prefChipSelected: { backgroundColor: '#8B5CF615', borderColor: '#8B5CF6' },
  prefChipText: { color: '#9CA3AF', fontSize: 13 },
  prefChipTextSelected: { color: '#8B5CF6', fontWeight: '600' },
  resetButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 24, paddingVertical: 12 },
  resetButtonText: { color: '#9CA3AF', fontSize: 14 },
  
  // End Meeting Button
  endMeetingBtn: { paddingVertical: 8, paddingHorizontal: 16, backgroundColor: '#EF444420', borderRadius: 20, borderWidth: 1, borderColor: '#EF4444' },
  endMeetingText: { color: '#EF4444', fontSize: 14, fontWeight: '600' },
  
  // Inactivity Prompt
  inactivityPrompt: { position: 'absolute', bottom: 100, left: 16, right: 16, flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#F59E0B20', borderWidth: 1, borderColor: '#F59E0B', borderRadius: 12, padding: 12 },
  inactivityText: { flex: 1, color: '#F59E0B', fontSize: 14 },
  endMeetingPromptBtn: { backgroundColor: '#F59E0B', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8 },
  endMeetingPromptText: { color: '#1A1A2E', fontSize: 12, fontWeight: '600' },
  
  // Summary Screen Styles
  summaryContent: { flex: 1, padding: 16 },
  summarySection: { backgroundColor: '#2D2D3A', borderRadius: 16, padding: 16, marginBottom: 16 },
  summarySectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 14, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: '#374151' },
  summarySectionTitle: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  summaryPoint: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  summaryPointNumber: { color: '#8B5CF6', fontSize: 14, fontWeight: '700', width: 20 },
  summaryPointText: { flex: 1, color: '#E5E7EB', fontSize: 14, lineHeight: 20 },
  actionItem: { backgroundColor: '#1A1A2E', borderRadius: 10, padding: 12, marginBottom: 10 },
  actionItemHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  actionItemTask: { flex: 1, color: '#FFFFFF', fontSize: 14, lineHeight: 20 },
  actionItemMeta: { flexDirection: 'row', gap: 8, marginTop: 8, marginLeft: 28 },
  actionItemTag: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#2D2D3A', paddingVertical: 4, paddingHorizontal: 8, borderRadius: 6 },
  actionItemTagText: { color: '#9CA3AF', fontSize: 11 },
  highlightItem: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  highlightBullet: { color: '#F59E0B', fontSize: 16, fontWeight: '700' },
  highlightText: { flex: 1, color: '#E5E7EB', fontSize: 14, lineHeight: 20 },
  summaryActions: { flexDirection: 'row', gap: 12, marginTop: 8 },
  summaryActionBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#2D2D3A', paddingVertical: 14, borderRadius: 12 },
  summaryShareBtn: { backgroundColor: '#8B5CF6' },
  summaryActionText: { color: '#FFFFFF', fontSize: 15, fontWeight: '600' },
  emptySummary: { alignItems: 'center', justifyContent: 'center', paddingVertical: 60 },
  emptySummaryText: { color: '#6B7280', fontSize: 15, marginTop: 12 },
  doneButton: { backgroundColor: '#10B981', marginHorizontal: 16, marginBottom: 16, paddingVertical: 16, borderRadius: 12, alignItems: 'center' },
  doneButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  headerCenter: { alignItems: 'center', flex: 1 },
  headerRight: { width: 60, alignItems: 'flex-end' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12 },
  headerTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '700' },
});
