const React = require('react');
const TestRenderer = require('react-test-renderer');
const { Pressable, StyleSheet, Text } = require('react-native');

const mockPush = jest.fn();
let mockUnread = 7;

jest.mock('expo-router', () => ({ useRouter: () => ({ push: mockPush }) }));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
jest.mock('@/hooks/useAppTheme', () => ({
  useAppTheme: () => ({
    colors: {
      bg: '#080B09', card: '#121513', primary: '#4CAF50', text: '#FFFFFF', onPrimary: '#071008',
    },
  }),
}));
jest.mock('../hooks/useNotifications', () => ({
  useUnreadCount: () => ({ data: mockUnread }),
}));
jest.mock('lucide-react-native', () => {
  const { Text: MockText } = require('react-native');
  return { Bell: MockText };
});
jest.mock('@/components/ui', () => {
  const MockReact = require('react');
  const { Pressable: MockPressable, Text: MockText } = require('react-native');
  return {
    AgPressable: (props: any) => MockReact.createElement(MockPressable, props),
    AgText: (props: any) => MockReact.createElement(MockText, props),
  };
});

import { NotificationBell } from '../components/NotificationBell';

describe('NotificationBell', () => {
  beforeEach(() => {
    mockUnread = 7;
    mockPush.mockClear();
  });

  it('anchors the real unread count to the bell and opens notifications', async () => {
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(NotificationBell));
    });

    const badge = tree.root.findByProps({ testID: 'home-notification-badge' });
    expect(StyleSheet.flatten(badge.props.style).position).toBe('absolute');
    expect(badge.findByType(Text).props.children).toBe(7);

    tree.root.findByProps({ testID: 'home-notification-bell' }).props.onPress();
    expect(mockPush).toHaveBeenCalledWith('/notifications');
  });

  it('hides the badge when there are no unread notifications', async () => {
    mockUnread = 0;
    let tree: any;
    await TestRenderer.act(async () => {
      tree = TestRenderer.create(React.createElement(NotificationBell));
    });
    expect(tree.root.findAllByProps({ testID: 'home-notification-badge' })).toHaveLength(0);
  });
});
