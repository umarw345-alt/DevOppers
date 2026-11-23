import React from 'react';
import { Text, View } from 'react-native';
import { Button, C, Page, Steps, T, WalletCard, useWide } from '../theme';

const FEATURES = [
  ['A real website', 'Your resume becomes a clean portfolio page with its own link. Four designs, any accent color.'],
  ['A Wallet card', 'Your name, title and a QR code in Apple Wallet or Google Wallet. No app to install, nothing to print.'],
  ['You decide what is public', 'Hide your phone, email or location. Edit any time and the same QR code shows the update.'],
];

const FAQ = [
  ['Is it free?', 'Yes. Make an account with your email and you are done.'],
  ['Do recruiters need an app?', 'No. They point their phone camera at the QR code and your page opens.'],
  ['What files work?', 'PDF, JPG or PNG up to 4 MB. No resume yet? Start blank and type it in.'],
  ['Does it work on Android?', 'Yes. Android phones get the card in Google Wallet, iPhones in Apple Wallet.'],
];

export default function Landing({ onSignUp, onLogIn }: { onSignUp: () => void; onLogIn: () => void }) {
  const wide = useWide();
  const columns = { flexDirection: wide ? 'row' : 'column', gap: wide ? 64 : 40 } as const;
  return (
    <Page
      right={<>
        <Button label="Log in" kind="ghost" small onPress={onLogIn} />
        <Button label="Sign up" small onPress={onSignUp} />
      </>}
    >
      <View style={[columns, { alignItems: 'center', paddingVertical: wide ? 48 : 8 }]}>
        <View style={{ flex: wide ? 1 : undefined, width: '100%' }}>
          <Text style={T.overline}>FOR STUDENTS AT CAREER FAIRS</Text>
          <Text style={[T.title, { fontSize: wide ? 56 : 40, lineHeight: wide ? 62 : 46 }]}>Your resume as a website and a Wallet card.</Text>
          <Text style={[T.dim, { fontSize: 18, lineHeight: 28, marginTop: 16, maxWidth: 520 }]}>
            Upload your resume once. We turn it into a portfolio page and a Wallet card (Apple or Google) with a QR code. Recruiters scan
            it and see everything.
          </Text>
          <View style={[T.row, { marginTop: 28 }]}>
            <Button label="Create your card" onPress={onSignUp} />
            <Button label="Log in" kind="secondary" onPress={onLogIn} />
          </View>
          <Text style={[T.dim, { fontSize: 14, marginTop: 14 }]}>Free · takes about a minute</Text>
        </View>
        <View style={{ flex: wide ? 1 : undefined, width: '100%' }}>
          <WalletCard name="Maya Patel" headline="Software Engineering Student" color="#1E3A8A" url="https://devoppers.vercel.app" />
        </View>
      </View>

      <Section overline="HOW IT WORKS" title="Three steps">
        <Steps />
      </Section>

      <Section overline="WHAT YOU GET" title="Everything a recruiter needs, in one scan">
        <View style={{ flexDirection: wide ? 'row' : 'column', gap: 12 }}>
          {FEATURES.map(([title, detail]) => (
            <View key={title} style={[T.card, { flex: 1, marginBottom: 0 }]}>
              <Text style={[T.body, { fontWeight: '700', fontSize: 17 }]}>{title}</Text>
              <Text style={T.dim}>{detail}</Text>
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

      <View style={[T.card, { marginTop: 72, padding: wide ? 40 : 24, alignItems: wide ? 'center' : 'flex-start' }]}>
        <Text style={[T.title, { fontSize: 28, textAlign: wide ? 'center' : 'left' }]}>Ready for your next career fair?</Text>
        <Text style={[T.dim, { textAlign: wide ? 'center' : 'left' }]}>All you need is your resume and an email address.</Text>
        <Button label="Create your card" onPress={onSignUp} style={{ marginTop: 12 }} />
      </View>

      <View style={{ borderTopWidth: 1, borderColor: C.line, marginTop: 64, paddingTop: 24 }}>
        <Text style={[T.dim, { fontSize: 13 }]}>Portable Resume · Made by DevOppers for CMPE 131 at San José State University</Text>
      </View>
    </Page>
  );
}

function Section({ overline, title, children }: { overline: string; title: string; children: React.ReactNode }) {
  return (
    <View style={{ marginTop: 72 }}>
      <Text style={T.overline}>{overline}</Text>
      <Text style={[T.title, { fontSize: 28, marginBottom: 20 }]}>{title}</Text>
      {children}
    </View>
  );
}
