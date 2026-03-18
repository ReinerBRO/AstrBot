import { createVuetify } from 'vuetify';
import '@/assets/mdi-subset/materialdesignicons-subset.css';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { PersbotLightTheme } from '@/theme/LightTheme';
import { PersbotDarkTheme } from "@/theme/DarkTheme";

export default createVuetify({
  components,
  directives,

  theme: {
    defaultTheme: 'PersbotLightTheme',
    themes: {
      PersbotLightTheme,
      PersbotDarkTheme
    }
  },
  defaults: {
    VBtn: {},
    VCard: {
      rounded: 'lg'
    },
    VTextField: {
      rounded: 'lg'
    },
    VTooltip: {
      // set v-tooltip default location to top
      location: 'top'
    }
  }
});
