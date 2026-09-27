import { initializeApp } from 'firebase/app';
import {
  browserSessionPersistence, getAuth, getMultiFactorResolver, PhoneAuthProvider,
  multiFactor, PhoneMultiFactorGenerator, RecaptchaVerifier, setPersistence,
  signInWithEmailAndPassword, signOut, type AuthError, type MultiFactorError,
  type UserCredential
} from 'firebase/auth';
import { getConfig } from './config';
import { clearSignedIn, markSignedIn } from './sessionTimeout';

let authInstance: ReturnType<typeof getAuth> | null = null;
function auth() {
  if (!authInstance) authInstance = getAuth(initializeApp(getConfig().firebase));
  return authInstance;
}

export async function signInAdmin(email: string, password: string, invitationToken?: string): Promise<void> {
  const instance = auth();
  await setPersistence(instance, browserSessionPersistence);
  let credential: UserCredential;
  try {
    credential = await signInWithEmailAndPassword(instance, email, password);
  } catch (error) {
    const authError = error as AuthError;
    if (authError.code !== 'auth/multi-factor-auth-required') throw error;
    const resolver = getMultiFactorResolver(instance, authError as MultiFactorError);
    const hint = resolver.hints.find(item => item.factorId === PhoneMultiFactorGenerator.FACTOR_ID);
    if (!hint) throw new Error('Your enrolled multi-factor method is not supported by this portal.');
    const verifier = new RecaptchaVerifier(instance, 'admin-recaptcha', { size: 'invisible' });
    try {
      const verificationId = await new PhoneAuthProvider(instance).verifyPhoneNumber(
        { multiFactorHint: hint, session: resolver.session }, verifier
      );
      const code = window.prompt(`Enter the verification code sent to ${hint.displayName ?? 'your enrolled phone'}.`);
      if (!code) throw new Error('Multi-factor verification was cancelled.');
      credential = await resolver.resolveSignIn(
        PhoneMultiFactorGenerator.assertion(PhoneAuthProvider.credential(verificationId, code))
      );
    } finally { verifier.clear(); }
  }
  const factors = multiFactor(credential.user);
  if (factors.enrolledFactors.length === 0) {
    const phoneNumber = window.prompt(
      'Enter the owner phone number with country code (for example, +919876543210) to enable MFA.',
    );
    if (!phoneNumber?.trim()) {
      await signOut(instance);
      throw new Error('Multi-factor enrolment is required for Admin access.');
    }
    const verifier = new RecaptchaVerifier(instance, 'admin-recaptcha', { size: 'invisible' });
    try {
      const session = await factors.getSession();
      const verificationId = await new PhoneAuthProvider(instance).verifyPhoneNumber(
        { phoneNumber: phoneNumber.trim(), session },
        verifier,
      );
      const code = window.prompt('Enter the verification code sent to the owner phone.');
      if (!code) throw new Error('Multi-factor enrolment was cancelled.');
      await factors.enroll(
        PhoneMultiFactorGenerator.assertion(PhoneAuthProvider.credential(verificationId, code)),
        'AgrowAI Admin phone',
      );
    } finally {
      verifier.clear();
    }
  }
  const idToken = await credential.user.getIdToken(true);
  if (invitationToken?.trim()) {
    const acceptance = await fetch(`${getConfig().apiBaseUrl}/admin/invitations/accept`, {
      method: 'POST', credentials: 'include',
      headers: { Authorization: `Bearer ${idToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: invitationToken.trim() })
    });
    if (!acceptance.ok) {
      await signOut(instance);
      throw new Error('This invitation is invalid, expired, used, or belongs to another email.');
    }
  }
  const response = await fetch(`${getConfig().apiBaseUrl}/admin/web-session`, {
    method: 'POST', credentials: 'include', headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!response.ok) {
    await signOut(instance);
    throw new Error(response.status === 403 ? 'This account is not authorised for AgrowAI Admin.' : 'Secure session could not be created.');
  }
  markSignedIn();
  await signOut(instance);
}

export async function signOutAdmin(csrf: string | null): Promise<void> {
  const response = await fetch(`${getConfig().apiBaseUrl}/admin/web-session`, {
    method: 'DELETE', credentials: 'include', headers: csrf ? { 'X-CSRF-Token': csrf } : {}
  });
  if (!response.ok) throw new Error('Secure sign-out failed. Check the connection and try again.');
  clearSignedIn();
}
