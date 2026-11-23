import React from 'react';
import { Text, View } from 'react-native';
import { TEMPLATES } from '../api';
import { Badge, BrowserMock, Button, C, Icon, Page, Steps, T, WalletCard, useWide } from '../theme';

const FEATURES = [
  ['▤', 'A real website', 'Your resume becomes a clean portfolio page with its own link. Four designs, any accent color.'],
  ['▣', 'A Wallet card', 'Your name, title and a QR code in Apple Wallet or Google Wallet. No app to install, nothing to print.'],
  ['◐', 'You decide what is public', 'Hide your phone, email or location. Edit any time and the same QR code shows the update.'],
];

const FAQ = [
  ['Is it free?', 'Yes. Make an account with your email or Google and you are done.'],
  ['Do recruiters need an app?', 'No. They point their phone camera at the QR code and your page opens.'],
  ['What files work?', 'PDF, JPG or PNG up to 4 MB. No resume yet? Start blank and type it in.'],
  ['Does it work on Android?', 'Yes. Android phones get the card in Google Wallet, iPhones in Apple Wallet.'],
];

export default function Landing({ onSignUp, onLogIn }: { onSignUp: () => void; onLogIn: () => void }) {
  const wide = useWide();
  return (
    <Page
      right={<>
        <Button label="Log in" kind="ghost" small onPress={onLogIn} />
        <Button label="Get started" small onPress={onSignUp} />
      </>}
    >
      <View style={{ flexDirection: wide ? 'row' : 'column', gap: wide ? 56 : 40, alignItems: 'center', paddingVertical: wide ? 40 : 4 }}>
        <View style={{ flex: wide ? 1 : undefined, width: '100%' }}>
          <Badge label="Made for SJSU career fairs" />
          <Text style={[T.title, { fontSize: wide ? 58 : 40, lineHeight: wide ? 64 : 46 }]}>
            Your resume,{'\n'}<Text style={{ color: C.accent }}>one scan away.</Text>
          </Text>
          <Text style={[T.dim, { fontSize: 18, lineHeight: 28, marginTop: 18, maxWidth: 500 }]}>
            Upload your resume once. Get a portfolio website and a Wallet card with a QR code. Recruiters scan it and see
            everything about you.
          </Text>
          <View style={[T.row, { marginTop: 28 }]}>
            <Button label="Create your card" onPress={onSignUp} />
            <Button label="I have an account" kind="secondary" onPress={onLogIn} />
          </View>
          <View style={[T.row, { marginTop: 28, gap: 28 }]}>
            {[['1 min', 'to set up'], ['4', 'designs'], ['0', 'apps to install']].map(([big, small]) => (
              <View key={small}>
                <Text style={{ color: C.text, fontSize: 22, fontWeight: '700' }}>{big}</Text>
                <Text style={[T.dim, { fontSize: 13 }]}>{small}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={{ flex: wide ? 1 : undefined, width: '100%', paddingBottom: wide ? 0 : 8 }}>
          <View style={{ marginRight: wide ? 90 : 0 }}>
            <BrowserMock url="devoppers.vercel.app/maya-patel" name="Maya Patel" headline="Software Engineering Student" color="#1E3A8A" />
          </View>
          <View style={wide ? { position: 'absolute', right: 0, bottom: -40, width: 230 } : { marginTop: -24, paddingHorizontal: 40 }}>
            <WalletCard name="Maya Patel" headline="SWE Student" color="#1E3A8A" url="https://devoppers.vercel.app/maya-patel" compact />
          </View>
        </View>
      </View>

      <Section overline="HOW IT WORKS" title="Three steps, about a minute">
        <Steps />
      </Section>

      <Section overline="WHAT YOU GET" title="Everything a recruiter needs, in one scan">
        <View style={{ flexDirection: wide ? 'row' : 'column', gap: 12 }}>
          {FEATURES.map(([glyph, title, detail]) => (
            <View key={title} style={[T.card, { flex: 1, marginBottom: 0 }]}>
              <Icon glyph={glyph} />
              <Text style={[T.body, { fontWeight: '700', fontSize: 17 }]}>{title}</Text>
              <Text style={T.dim}>{detail}</Text>
            </View>
          ))}
        </View>
      </Section>

      <Section overline="DESIGNS" title="Pick a look, change it any time">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
          {Object.entries(TEMPLATES).map(([name, color]) => (
            <View key={name} style={[T.card, { marginBottom: 0, flexGrow: 1, flexBasis: wide ? 0 : '45%', padding: 14 }]}>
              <View style={{ height: 84, borderRadius: 10, backgroundColor: name === 'dark' ? C.text : color, justifyContent: 'flex-end', padding: 12 }}>
                <View style={{ height: 6, width: '55%', borderRadius: 3, backgroundColor: name === 'dark' ? color : '#FFFFFF' }} />
              </View>
              <Text style={[T.body, { fontWeight: '600', marginTop: 4 }]}>{name[0].toUpperCase() + name.slice(1)}</Text>
            </View>
          ))}
        </View>
      </Section>

      <Section overline="QUESTIONS" title="Good to know">
        <View style={{ flexDirection: wide ? 'row' : 'column', flexWrap: 'wrap', gap: 12 }}>
          {FAQ.map(([q, a]) => (
            <View key={q} style={[T.card, { marginBottom: 0, flexBasis: wide ? '48%' : 'auto', flexGrow: 1 }]}>
              <Text style={[T.body, { fontWeight: '700' }]}>{q}</Text>
              <Text style={T.dim}>{a}</Text>
            </View>
          ))}
        </View>
      </Section>

      <View style={{ marginTop: 80, borderRadius: 24, backgroundColor: C.accent, padding: wide ? 48 : 28, alignItems: wide ? 'center' : 'flex-start', gap: 10 }}>
        <Text style={[T.title, { color: '#FFFFFF', fontSize: wide ? 34 : 28, textAlign: wide ? 'center' : 'left' }]}>Ready for your next career fair?</Text>
        <Text style={{ color: '#E0E3FF', fontSize: 16, textAlign: wide ? 'center' : 'left' }}>All you need is your resume and an email address.</Text>
        <Button label="Create your card" kind="secondary" onPress={onSignUp} style={{ marginTop: 8 }} />
      </View>

      <View style={[T.row, { justifyContent: 'space-between', borderTopWidth: 1, borderColor: C.line, marginTop: 56, paddingTop: 24 }]}>
        <Text style={[T.dim, { fontSize: 13 }]}>Portable Resume · DevOppers, CMPE 131, San José State University</Text>
        <View style={T.row}>
          <Button label="Log in" kind="ghost" small onPress={onLogIn} />
          <Button label="Sign up" kind="ghost" small onPress={onSignUp} />
        </View>
      </View>
    </Page>
  );
}

function Section({ overline, title, children }: { overline: string; title: string; children: React.ReactNode }) {
  return (
    <View style={{ marginTop: 88 }}>
      <Text style={T.overline}>{overline}</Text>
      <Text style={[T.title, { fontSize: 30, marginBottom: 22 }]}>{title}</Text>
      {children}
    </View>
  );
}
