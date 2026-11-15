// ESLint settings ("flat config"). ESLint finds mistakes; Prettier handles layout.

import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  { ignores: ["dist", "node_modules"] },

  js.configs.recommended,
  // "strict" adds rules that catch likely bugs; "TypeChecked" lets rules use type
  // information, for example to find a promise nobody waits for.
  tseslint.configs.strictTypeChecked,

  {
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: { allowDefaultProject: ["eslint.config.js"] },
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // SR-35: never insert raw HTML. Semgrep checks this in CI as well; having it here
      // too shows the error in the editor while typing.
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: "Raw HTML bypasses React's escaping (SR-35). Render through components.",
        },
        {
          selector: "AssignmentExpression[left.property.name=/^(innerHTML|outerHTML)$/]",
          message: "Raw HTML is not allowed (SR-35). Use textContent or components.",
        },
      ],
      "no-console": "error",
      eqeqeq: "error",
    },
  },
);
