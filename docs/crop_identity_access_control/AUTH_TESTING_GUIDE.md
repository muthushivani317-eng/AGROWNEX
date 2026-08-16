# Authentication testing

Unit and mocked ASGI integration tests prove database role enforcement,
farmer/missing/unknown/conflicting-role denial, disabled-user denial, client
role-override rejection, controlled-role access, token redaction, and zero
upload/model work before authorization.

Firebase verification is mocked in local tests. No production secret or real
identity is used. Therefore real Firebase HTTP authentication, revocation, and
expired-token HTTP tests remain `NOT_AVAILABLE` until a Firebase Auth Emulator
or dedicated test project is configured.
