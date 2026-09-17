const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const config = getDefaultConfig(__dirname);

// expo-sqlite's web worker loads wa-sqlite as WebAssembly. Keep it in Metro's
// asset pipeline so production web exports can resolve and copy the binary.
if (!config.resolver.assetExts.includes('wasm')) {
  config.resolver.assetExts.push('wasm');
}

module.exports = withNativeWind(config, { input: './global.css' });
