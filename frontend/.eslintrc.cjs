module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    // Отключаем правило, если вам мешают any в аналитике (временно для скорости)
    '@typescript-eslint/no-explicit-any': 'off',
    // Предупреждать о неиспользуемых переменных
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePatt