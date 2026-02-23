/**
 * Chart Theme Configuration
 * 
 * Recharts theme settings for dark/light mode
 */

export interface ChartTheme {
  text: string;
  grid: string;
  background: string;
  tooltip: {
    background: string;
    border: string;
    text: string;
  };
}

export const getLightTheme = (): ChartTheme => ({
  text: '#1F2937',
  grid: '#E5E7EB',
  background: '#FFFFFF',
  tooltip: {
    background: '#FFFFFF',
    border: '#E5E7EB',
    text: '#1F2937'
  }
});

export const getDarkTheme = (): ChartTheme => ({
  text: '#E5E7EB',
  grid: '#374151',
  background: '#1F2937',
  tooltip: {
    background: '#1F2937',
    border: '#374151',
    text: '#E5E7EB'
  }
});

export const getChartTheme = (darkMode: boolean): ChartTheme => {
  return darkMode ? getDarkTheme() : getLightTheme();
};

