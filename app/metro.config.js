// Lets the app import the shared feedback catalog from ../feedback, so the
// Python decision module and the app use the same interventions.json.
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
config.watchFolders = [path.resolve(__dirname, '../feedback')];

module.exports = config;
