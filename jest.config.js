module.exports = {
  preset: '@react-native/jest-preset',
  cacheDirectory: '<rootDir>/.jest-cache',
  setupFiles: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^expo/virtual/env(?:\\.js)?$': '<rootDir>/__mocks__/expo-virtual-env.js',
  },
};
