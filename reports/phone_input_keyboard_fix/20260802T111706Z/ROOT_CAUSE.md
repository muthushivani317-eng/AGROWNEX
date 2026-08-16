# Root cause

The visible control was a real, enabled, non-zero native `ReactEditText`. Live logcat proved Android issued `SHOW_SOFT_INPUT`, then the `AgInput` `onFocus` handler changed React state, rerendered the focus-sensitive input subtree, invalidated the input connection, and immediately caused `HIDE_SOFT_INPUT`. The hierarchy ended with `focused=false`.

The fix removes the focus-time React rerender. Border feedback now uses an imperative native style update, while the whole field wrapper directly calls the native input ref's `focus()` method.
