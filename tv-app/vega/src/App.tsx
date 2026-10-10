/**
 * Vibe for Fire TV (Vega OS) — a thin React Native shell around the Vibe web app.
 *
 * - Full-screen WebView with TV focus, black background (no white flash)
 * - Remote keys (D-pad, select, back, play/pause) are delivered to the web app
 * - The web app talks back via postMessage: {type: 'exit'} closes the app at the home screen,
 *   {type: 'launch', provider, title, link} tries to hand off to the streaming app
 */
import * as React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { BackHandler, Linking, StyleSheet, Text, View } from 'react-native';
import { WebView } from '@amazon-devices/webview';
import { VIBE_URL } from './config';

const BACK_JS = "window.dispatchEvent(new CustomEvent('vibe:back')); true;";

export const App = () => {
  const webRef = useRef<any>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  // Hardware back → the web app decides (close a dialog, go to the previous screen, or ask to exit).
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      webRef.current?.injectJavaScript(BACK_JS);
      return true;
    });
    return () => sub.remove();
  }, []);

  const onMessage = useCallback((event: any) => {
    let msg: any = null;
    try {
      msg = JSON.parse(event?.nativeEvent?.data ?? '{}');
    } catch {
      return;
    }
    if (msg?.type === 'exit') {
      BackHandler.exitApp();
    } else if (msg?.type === 'launch' && msg.link) {
      // Best effort: provider deep links differ by app and OS build. Falls back silently.
      Linking.openURL(msg.link).catch(() => undefined);
    }
  }, []);

  if (failed) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>vibe</Text>
        <Text style={styles.body}>Can’t reach Vibe. Check the network and VIBE_URL.</Text>
        <Text style={styles.small}>{failed}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <WebView
        key={attempt}
        ref={webRef}
        style={styles.webview}
        source={{ uri: VIBE_URL }}
        hasTVPreferredFocus={true}
        javaScriptEnabled={true}
        allowSystemKeyEvents={true}
        mediaPlaybackRequiresUserAction={false}
        onMessage={onMessage}
        onError={(e: any) => {
          setFailed(String(e?.nativeEvent?.description ?? e?.nativeEvent?.url ?? 'load error'));
          setTimeout(() => {
            setFailed(null);
            setAttempt((a) => a + 1);
          }, 5000);
        }}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#08080a' },
  webview: { flex: 1, backgroundColor: '#08080a' },
  center: { flex: 1, backgroundColor: '#08080a', alignItems: 'center', justifyContent: 'center' },
  title: { color: '#f4f1ea', fontSize: 64, marginBottom: 16 },
  body: { color: '#a8a39a', fontSize: 24 },
  small: { color: '#6f6b64', fontSize: 16, marginTop: 8 },
});
