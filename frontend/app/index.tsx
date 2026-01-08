import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Platform,
  StatusBar,
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width } = Dimensions.get('window');

// API Configuration
const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// Types
type Mode = 'interview' | 'business' | 'sales' | 'general';

interface Suggestion {
  text: string;
  tone: string;
  priority: number;
}

interface ModeConfig {
  id: Mode;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  description: string;
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

// Speech Recognition Simulation (since expo-speech only does TTS)
// In production, you'd use a native module or cloud service
const useSpeechRecognition = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recordingRef = useRef<Audio.Recording | null>(null);

  const startListening = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Please grant microphone access to use this feature.');
        return false;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await recording.startAsync();
      recordingRef.current = recording;
      setIsListening(true);
      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      return false;
    }
  };

  const stopListening = async () => {
    try {
      if (recordingRef.current) {
        await recordingRef.current.stopAndUnloadAsync();
        recordingRef.current = null;
      }
      setIsListening(false);
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  return {
    isListening,
    transcript,
    setTranscript,
    startListening,
    stopListening,
  };
};

export default function WhisprlyApp() {
  // State
  const [currentScreen, setCurrentScreen] = useState<'home' | 'session'>('home');
  const [selectedMode, setSelectedMode] = useState<Mode>('general');
  const [sessionId, setSessionId] = useState<string>('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [detectedQuestion, setDetectedQuestion] = useState(false);
  const [questionContext, setQuestionContext] = useState<string | null>(null);
  const [conversationContext, setConversationContext] = useState<string[]>([]);
  const [inputText, setInputText] = useState('');

  // Speech recognition hook
  const {
    isListening,
    transcript,
    setTranscript,
    startListening,
    stopListening,
  } = useSpeechRecognition();

  // Animations
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Pulse animation for listening indicator
  useEffect(() => {
    if (isListening) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    }
  }, [isListening]);

  // Fade in suggestions
  useEffect(() => {
    if (suggestions.length > 0) {
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [suggestions]);

  // Create session
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

  // Fetch suggestions from API
  const fetchSuggestions = async (text: string) => {
    if (!text.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: text,
          mode: selectedMode,
          session_id: sessionId,
          context: conversationContext,
        }),
      });

      if (!response.ok) throw new Error('API request failed');

      const data = await response.json();
      setSuggestions(data.suggestions || []);
      setDetectedQuestion(data.detected_question || false);
      setQuestionContext(data.question_context || null);
      setConversationContext((prev) => [...prev, text].slice(-10));
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
      // Fallback suggestions
      setSuggestions([
        { text: 'Could you tell me more about that?', tone: 'curious', priority: 1 },
        { text: "That's interesting. I'd like to add...", tone: 'engaged', priority: 2 },
        { text: 'I understand your point.', tone: 'empathetic', priority: 3 },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle mode selection and start session
  const handleStartSession = async (mode: Mode) => {
    setSelectedMode(mode);
    const newSessionId = await createSession(mode);
    setSessionId(newSessionId);
    setSuggestions([]);
    setConversationContext([]);
    setDetectedQuestion(false);
    setQuestionContext(null);
    setCurrentScreen('session');
  };

  // Handle listening toggle
  const handleToggleListening = async () => {
    if (isListening) {
      await stopListening();
      // In a real app, you'd get the transcription here
      // For now, we'll use a simulated input
    } else {
      await startListening();
    }
  };

  // Handle manual input submit
  const handleSubmitInput = () => {
    if (inputText.trim()) {
      fetchSuggestions(inputText);
      setInputText('');
    }
  };

  // End session
  const handleEndSession = () => {
    stopListening();
    setSuggestions([]);
    setConversationContext([]);
    setSessionId('');
    setCurrentScreen('home');
  };

  // Copy suggestion to clipboard
  const handleCopySuggestion = (text: string) => {
    // In a real app, use Clipboard API
    Alert.alert('Copied!', 'Suggestion copied to clipboard');
  };

  // Get mode config
  const getModeConfig = (mode: Mode) => MODES.find((m) => m.id === mode)!;

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
        <Text style={styles.tagline}>Silent conversation companion</Text>
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
              activeOpacity={0.8}
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
          Tap a mode to start your session
        </Text>
      </View>
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
          </View>
          <View style={styles.headerSpacer} />
        </View>

        {/* Question Alert */}
        {detectedQuestion && questionContext && (
          <View style={styles.questionAlert}>
            <Ionicons name="help-circle" size={20} color="#F59E0B" />
            <Text style={styles.questionAlertText}>
              Question detected: {questionContext}
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
              {suggestions.map((suggestion, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionCard}
                  onPress={() => handleCopySuggestion(suggestion.text)}
                  activeOpacity={0.8}
                >
                  <View style={styles.suggestionHeader}>
                    <View style={styles.priorityBadge}>
                      <Text style={styles.priorityText}>#{suggestion.priority}</Text>
                    </View>
                    <View style={styles.toneBadge}>
                      <Text style={styles.toneText}>{suggestion.tone}</Text>
                    </View>
                  </View>
                  <Text style={styles.suggestionText}>{suggestion.text}</Text>
                  <View style={styles.suggestionFooter}>
                    <Ionicons name="copy-outline" size={16} color="#6B7280" />
                    <Text style={styles.tapToCopy}>Tap to copy</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </Animated.View>
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="chatbubble-ellipses-outline" size={48} color="#4B5563" />
              <Text style={styles.emptyStateTitle}>Ready to assist</Text>
              <Text style={styles.emptyStateText}>
                Tap the microphone to start listening{"\n"}
                or type what you're hearing
              </Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <View style={styles.textInputContainer}>
            <TouchableOpacity
              style={styles.textInputWrapper}
              onPress={() => {
                const sampleInputs = [
                  "Can you tell me about your experience with project management?",
                  "What makes your product different from competitors?",
                  "How would you handle a difficult team member?",
                  "What are your thoughts on the budget proposal?",
                  "Could you walk me through your sales process?",
                ];
                const randomInput = sampleInputs[Math.floor(Math.random() * sampleInputs.length)];
                fetchSuggestions(randomInput);
              }}
            >
              <Ionicons name="text-outline" size={20} color="#6B7280" />
              <Text style={styles.textInputPlaceholder}>
                Tap to simulate input...
              </Text>
            </TouchableOpacity>
          </View>

          {/* Microphone Button */}
          <TouchableOpacity
            style={[
              styles.micButton,
              isListening && styles.micButtonActive,
              { backgroundColor: modeConfig.color },
            ]}
            onPress={handleToggleListening}
            activeOpacity={0.8}
          >
            <Animated.View style={{ transform: [{ scale: isListening ? pulseAnim : 1 }] }}>
              <Ionicons
                name={isListening ? 'mic' : 'mic-outline'}
                size={28}
                color="#FFFFFF"
              />
            </Animated.View>
          </TouchableOpacity>
        </View>

        {/* Listening Indicator */}
        {isListening && (
          <View style={styles.listeningIndicator}>
            <View style={styles.listeningDot} />
            <Text style={styles.listeningText}>Listening...</Text>
          </View>
        )}
      </SafeAreaView>
    );
  };

  // Main render
  return currentScreen === 'home' ? renderHomeScreen() : renderSessionScreen();
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

  questionAlert: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    marginHorizontal: 16,
    padding: 12,
    borderRadius: 12,
    gap: 8,
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
  suggestionFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  tapToCopy: {
    color: '#6B7280',
    fontSize: 12,
  },

  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
  },
  emptyStateTitle: {
    color: '#FFFFFF',
    fontSize: 18,
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

  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: '#2D2D3A',
  },
  textInputContainer: {
    flex: 1,
  },
  textInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
  },
  textInputPlaceholder: {
    color: '#6B7280',
    fontSize: 14,
  },

  micButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
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

  listeningIndicator: {
    position: 'absolute',
    bottom: 100,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A24',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 8,
  },
  listeningDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#EF4444',
  },
  listeningText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '500',
  },
});
