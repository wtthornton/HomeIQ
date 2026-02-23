/**
 * SetupWizard Component
 * 
 * 3-step wizard for team selection and configuration
 */

import React, { useState, useEffect } from 'react';
import { TeamSelector } from './TeamSelector';
import type { Team } from '../../types/sports';
import { calculateAPIUsage, getUsageColor, getProgressBarColor } from '../../utils/apiUsageCalculator';

interface SetupWizardProps {
  onComplete: (nflTeams: string[], nhlTeams: string[]) => void;
  onCancel?: () => void;
  darkMode?: boolean;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({
  onComplete,
  onCancel,
  darkMode = false
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [nflTeams, setNflTeams] = useState<string[]>([]);
  const [nhlTeams, setNhlTeams] = useState<string[]>([]);
  const [availableNFLTeams, setAvailableNFLTeams] = useState<Team[]>([]);
  const [availableNHLTeams, setAvailableNHLTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);

  const bgPrimary = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const bgCard = darkMode ? 'bg-gray-800' : 'bg-white';
  const bgSecondary = darkMode ? 'bg-gray-700' : 'bg-gray-50';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  // Fetch available teams
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        // Fetch NFL teams
        const nflResponse = await fetch('/api/sports/teams?league=NFL');
        const nflData = await nflResponse.json();
        setAvailableNFLTeams(nflData.teams || []);

        // Fetch NHL teams
        const nhlResponse = await fetch('/api/sports/teams?league=NHL');
        const nhlData = await nhlResponse.json();
        setAvailableNHLTeams(nhlData.teams || []);
      } catch (error) {
        console.error('Error fetching teams:', error);
        // Use fallback static data if API fails
        setAvailableNFLTeams(getStaticNFLTeams());
        setAvailableNHLTeams(getStaticNHLTeams());
      } finally {
        setLoading(false);
      }
    };

    fetchTeams();
  }, []);

  const handleNFLTeamToggle = (teamId: string) => {
    setNflTeams(prev => 
      prev.includes(teamId)
        ? prev.filter(id => id !== teamId)
        : [...prev, teamId]
    );
  };

  const handleNHLTeamToggle = (teamId: string) => {
    setNhlTeams(prev =>
      prev.includes(teamId)
        ? prev.filter(id => id !== teamId)
        : [...prev, teamId]
    );
  };

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = () => {
    onComplete(nflTeams, nhlTeams);
  };

  const canContinue = () => {
    if (currentStep === 1) {
      // Must select at least 1 NFL team
      return nflTeams.length > 0;
    }
    return true; // NHL is optional
  };

  const apiUsage = calculateAPIUsage(nflTeams, nhlTeams);

  if (loading) {
    return (
      <div className={`min-h-screen ${bgPrimary} flex items-center justify-center`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
          <p className={textSecondary}>Loading teams...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${bgPrimary} py-12 px-4`}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className={`${bgCard} rounded-xl shadow-xl p-8 mb-8`}>
          <h1 className={`text-3xl font-bold ${textPrimary} mb-2`}>
            🏈🏒 Sports Integration Setup
          </h1>
          <p className={textSecondary}>
            Step {currentStep} of 3: {
              currentStep === 1 ? 'Select NFL Teams' :
                currentStep === 2 ? 'Select NHL Teams (Optional)' :
                  'Review & Confirm'
            }
          </p>
          
          {/* Progress Indicators */}
          <div className="flex items-center gap-2 mt-6">
            {[1, 2, 3].map(step => (
              <div
                key={step}
                className={`flex-1 h-2 rounded-full transition-colors ${
                  step <= currentStep
                    ? 'bg-blue-500'
                    : darkMode ? 'bg-gray-700' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className={`${bgCard} rounded-xl shadow-xl p-8`}>
          {/* Step 1: NFL Teams */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
                  🏈 Select Your NFL Teams
                </h2>
                <p className={textSecondary}>
                  Choose the teams you want to track. We recommend selecting 3-5 teams.
                </p>
              </div>

              <TeamSelector
                league="NFL"
                teams={availableNFLTeams}
                selectedTeams={nflTeams}
                onTeamToggle={handleNFLTeamToggle}
                darkMode={darkMode}
              />
            </div>
          )}

          {/* Step 2: NHL Teams */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
                  🏒 Select Your NHL Teams (Optional)
                </h2>
                <p className={textSecondary}>
                  Add NHL teams to your dashboard, or skip this step to continue with NFL only.
                </p>
              </div>

              <TeamSelector
                league="NHL"
                teams={availableNHLTeams}
                selectedTeams={nhlTeams}
                onTeamToggle={handleNHLTeamToggle}
                darkMode={darkMode}
              />
            </div>
          )}

          {/* Step 3: Review */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className={`text-2xl font-bold ${textPrimary} mb-2`}>
                  ✅ Review Your Selections
                </h2>
                <p className={textSecondary}>
                  Confirm your team selections and estimated API usage.
                </p>
              </div>

              {/* Selected Teams Summary */}
              <div className="space-y-4">
                {/* NFL Teams */}
                {nflTeams.length > 0 && (
                  <div className={`p-4 rounded-lg ${bgSecondary}`}>
                    <h3 className={`font-semibold ${textPrimary} mb-3`}>
                      🏈 NFL Teams ({nflTeams.length}):
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {nflTeams.map(teamId => {
                        const team = availableNFLTeams.find(t => t.id === teamId);
                        return team ? (
                          <div
                            key={teamId}
                            className={`px-3 py-2 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-white'} 
                              ${textPrimary} text-sm font-medium flex items-center gap-2`}
                          >
                            🏈 {team.name}
                          </div>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}

                {/* NHL Teams */}
                {nhlTeams.length > 0 && (
                  <div className={`p-4 rounded-lg ${bgSecondary}`}>
                    <h3 className={`font-semibold ${textPrimary} mb-3`}>
                      🏒 NHL Teams ({nhlTeams.length}):
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {nhlTeams.map(teamId => {
                        const team = availableNHLTeams.find(t => t.id === teamId);
                        return team ? (
                          <div
                            key={teamId}
                            className={`px-3 py-2 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-white'} 
                              ${textPrimary} text-sm font-medium flex items-center gap-2`}
                          >
                            🏒 {team.name}
                          </div>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* API Usage Estimate */}
              <div className={`p-6 rounded-lg ${darkMode ? 'bg-blue-900/20 border-2 border-blue-500/30' : 'bg-blue-50 border-2 border-blue-200'}`}>
                <h3 className={`font-semibold ${textPrimary} mb-4`}>
                  📊 Estimated API Usage
                </h3>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className={textSecondary}>Daily API Calls:</span>
                    <span className={`font-bold text-xl ${getUsageColor(apiUsage.warning_level)}`}>
                      {apiUsage.daily_calls} / 100
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className={`h-3 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} overflow-hidden`}>
                    <div
                      className={`h-full ${getProgressBarColor(apiUsage.warning_level)} transition-all duration-300`}
                      style={{ width: `${Math.min(100, (apiUsage.daily_calls / 100) * 100)}%` }}
                    />
                  </div>

                  <div className={`text-sm ${textSecondary}`}>
                    {apiUsage.recommendation}
                  </div>

                  {!apiUsage.within_free_tier && (
                    <div className="text-sm text-red-600 dark:text-red-400 font-semibold">
                      ⚠️ Exceeds free tier limit. Consider removing teams or upgrading to paid API.
                    </div>
                  )}
                </div>
              </div>

              {/* Important Notice */}
              <div className={`p-4 rounded-lg ${darkMode ? 'bg-yellow-900/20 border border-yellow-500/30' : 'bg-yellow-50 border border-yellow-200'}`}>
                <p className={`text-sm ${darkMode ? 'text-yellow-200' : 'text-yellow-800'}`}>
                  ⚠️ <strong>Important:</strong> Only these teams will be monitored. 
                  You can add or remove teams anytime in the Settings tab.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={currentStep === 1 ? onCancel : handleBack}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
              }`}
            >
              {currentStep === 1 ? 'Cancel' : '← Back'}
            </button>

            <div className="flex gap-3">
              {/* Skip NHL button on step 2 */}
              {currentStep === 2 && (
                <button
                  onClick={handleNext}
                  className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-white'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                  }`}
                >
                  Skip NHL →
                </button>
              )}

              {/* Continue/Complete button */}
              <button
                onClick={currentStep === 3 ? handleComplete : handleNext}
                disabled={!canContinue()}
                className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                  canContinue()
                    ? darkMode
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-blue-500 hover:bg-blue-600 text-white'
                    : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                }`}
              >
                {currentStep === 3 ? '✓ Confirm & Start' : 'Continue →'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Fallback static team data if API fails
function getStaticNFLTeams(): Team[] {
  return [
    // AFC East
    { id: 'buf', name: 'Buffalo Bills', abbreviation: 'BUF', logo: '', colors: { primary: '#00338D', secondary: '#C60C30' } },
    { id: 'mia', name: 'Miami Dolphins', abbreviation: 'MIA', logo: '', colors: { primary: '#008E97', secondary: '#FC4C02' } },
    { id: 'ne', name: 'New England Patriots', abbreviation: 'NE', logo: '', colors: { primary: '#002244', secondary: '#C60C30' } },
    { id: 'nyj', name: 'New York Jets', abbreviation: 'NYJ', logo: '', colors: { primary: '#125740', secondary: '#FFFFFF' } },
    // AFC North
    { id: 'bal', name: 'Baltimore Ravens', abbreviation: 'BAL', logo: '', colors: { primary: '#241773', secondary: '#000000' } },
    { id: 'cin', name: 'Cincinnati Bengals', abbreviation: 'CIN', logo: '', colors: { primary: '#FB4F14', secondary: '#000000' } },
    { id: 'cle', name: 'Cleveland Browns', abbreviation: 'CLE', logo: '', colors: { primary: '#311D00', secondary: '#FF3C00' } },
    { id: 'pit', name: 'Pittsburgh Steelers', abbreviation: 'PIT', logo: '', colors: { primary: '#FFB612', secondary: '#101820' } },
    // AFC South
    { id: 'hou', name: 'Houston Texans', abbreviation: 'HOU', logo: '', colors: { primary: '#03202F', secondary: '#A71930' } },
    { id: 'ind', name: 'Indianapolis Colts', abbreviation: 'IND', logo: '', colors: { primary: '#002C5F', secondary: '#A2AAAD' } },
    { id: 'jax', name: 'Jacksonville Jaguars', abbreviation: 'JAX', logo: '', colors: { primary: '#006778', secondary: '#D7A22A' } },
    { id: 'ten', name: 'Tennessee Titans', abbreviation: 'TEN', logo: '', colors: { primary: '#0C2340', secondary: '#4B92DB' } },
    // AFC West
    { id: 'den', name: 'Denver Broncos', abbreviation: 'DEN', logo: '', colors: { primary: '#FB4F14', secondary: '#002244' } },
    { id: 'kc', name: 'Kansas City Chiefs', abbreviation: 'KC', logo: '', colors: { primary: '#E31837', secondary: '#FFB81C' } },
    { id: 'lv', name: 'Las Vegas Raiders', abbreviation: 'LV', logo: '', colors: { primary: '#000000', secondary: '#A5ACAF' } },
    { id: 'lac', name: 'Los Angeles Chargers', abbreviation: 'LAC', logo: '', colors: { primary: '#0080C6', secondary: '#FFC20E' } },
    // NFC East
    { id: 'dal', name: 'Dallas Cowboys', abbreviation: 'DAL', logo: '', colors: { primary: '#003594', secondary: '#869397' } },
    { id: 'nyg', name: 'New York Giants', abbreviation: 'NYG', logo: '', colors: { primary: '#0B2265', secondary: '#A5ACAF' } },
    { id: 'phi', name: 'Philadelphia Eagles', abbreviation: 'PHI', logo: '', colors: { primary: '#004C54', secondary: '#A5ACAF' } },
    { id: 'wsh', name: 'Washington Commanders', abbreviation: 'WSH', logo: '', colors: { primary: '#5A1414', secondary: '#FFB612' } },
    // NFC North
    { id: 'chi', name: 'Chicago Bears', abbreviation: 'CHI', logo: '', colors: { primary: '#0B162A', secondary: '#C83803' } },
    { id: 'det', name: 'Detroit Lions', abbreviation: 'DET', logo: '', colors: { primary: '#0076B6', secondary: '#B0B7BC' } },
    { id: 'gb', name: 'Green Bay Packers', abbreviation: 'GB', logo: '', colors: { primary: '#203731', secondary: '#FFB612' } },
    { id: 'min', name: 'Minnesota Vikings', abbreviation: 'MIN', logo: '', colors: { primary: '#4F2683', secondary: '#FFC62F' } },
    // NFC South
    { id: 'atl', name: 'Atlanta Falcons', abbreviation: 'ATL', logo: '', colors: { primary: '#A71930', secondary: '#000000' } },
    { id: 'car', name: 'Carolina Panthers', abbreviation: 'CAR', logo: '', colors: { primary: '#0085CA', secondary: '#101820' } },
    { id: 'no', name: 'New Orleans Saints', abbreviation: 'NO', logo: '', colors: { primary: '#D3BC8D', secondary: '#101820' } },
    { id: 'tb', name: 'Tampa Bay Buccaneers', abbreviation: 'TB', logo: '', colors: { primary: '#D50A0A', secondary: '#FF7900' } },
    // NFC West
    { id: 'ari', name: 'Arizona Cardinals', abbreviation: 'ARI', logo: '', colors: { primary: '#97233F', secondary: '#000000' } },
    { id: 'lar', name: 'Los Angeles Rams', abbreviation: 'LAR', logo: '', colors: { primary: '#003594', secondary: '#FFA300' } },
    { id: 'sf', name: 'San Francisco 49ers', abbreviation: 'SF', logo: '', colors: { primary: '#AA0000', secondary: '#B3995D' } },
    { id: 'sea', name: 'Seattle Seahawks', abbreviation: 'SEA', logo: '', colors: { primary: '#002244', secondary: '#69BE28' } },
  ];
}

function getStaticNHLTeams(): Team[] {
  return [
    // Atlantic Division
    { id: 'bos', name: 'Boston Bruins', abbreviation: 'BOS', logo: '', colors: { primary: '#FCB514', secondary: '#000000' } },
    { id: 'buf', name: 'Buffalo Sabres', abbreviation: 'BUF', logo: '', colors: { primary: '#002654', secondary: '#FCB514' } },
    { id: 'det', name: 'Detroit Red Wings', abbreviation: 'DET', logo: '', colors: { primary: '#CE1126', secondary: '#FFFFFF' } },
    { id: 'fla', name: 'Florida Panthers', abbreviation: 'FLA', logo: '', colors: { primary: '#041E42', secondary: '#C8102E' } },
    { id: 'mtl', name: 'Montreal Canadiens', abbreviation: 'MTL', logo: '', colors: { primary: '#AF1E2D', secondary: '#192168' } },
    { id: 'ott', name: 'Ottawa Senators', abbreviation: 'OTT', logo: '', colors: { primary: '#C52032', secondary: '#000000' } },
    { id: 'tbl', name: 'Tampa Bay Lightning', abbreviation: 'TBL', logo: '', colors: { primary: '#002868', secondary: '#FFFFFF' } },
    { id: 'tor', name: 'Toronto Maple Leafs', abbreviation: 'TOR', logo: '', colors: { primary: '#00205B', secondary: '#FFFFFF' } },
    // Metropolitan Division
    { id: 'car', name: 'Carolina Hurricanes', abbreviation: 'CAR', logo: '', colors: { primary: '#CC0000', secondary: '#000000' } },
    { id: 'cbj', name: 'Columbus Blue Jackets', abbreviation: 'CBJ', logo: '', colors: { primary: '#002654', secondary: '#CE1126' } },
    { id: 'njd', name: 'New Jersey Devils', abbreviation: 'NJD', logo: '', colors: { primary: '#CE1126', secondary: '#000000' } },
    { id: 'nyi', name: 'New York Islanders', abbreviation: 'NYI', logo: '', colors: { primary: '#00539B', secondary: '#F47D30' } },
    { id: 'nyr', name: 'New York Rangers', abbreviation: 'NYR', logo: '', colors: { primary: '#0038A8', secondary: '#CE1126' } },
    { id: 'phi', name: 'Philadelphia Flyers', abbreviation: 'PHI', logo: '', colors: { primary: '#F74902', secondary: '#000000' } },
    { id: 'pit', name: 'Pittsburgh Penguins', abbreviation: 'PIT', logo: '', colors: { primary: '#000000', secondary: '#FCB514' } },
    { id: 'wsh', name: 'Washington Capitals', abbreviation: 'WSH', logo: '', colors: { primary: '#041E42', secondary: '#C8102E' } },
    // Central Division
    { id: 'ari', name: 'Arizona Coyotes', abbreviation: 'ARI', logo: '', colors: { primary: '#8C2633', secondary: '#E2D6B5' } },
    { id: 'chi', name: 'Chicago Blackhawks', abbreviation: 'CHI', logo: '', colors: { primary: '#CF0A2C', secondary: '#000000' } },
    { id: 'col', name: 'Colorado Avalanche', abbreviation: 'COL', logo: '', colors: { primary: '#6F263D', secondary: '#236192' } },
    { id: 'dal', name: 'Dallas Stars', abbreviation: 'DAL', logo: '', colors: { primary: '#006847', secondary: '#8F8F8C' } },
    { id: 'min', name: 'Minnesota Wild', abbreviation: 'MIN', logo: '', colors: { primary: '#154734', secondary: '#A6192E' } },
    { id: 'nsh', name: 'Nashville Predators', abbreviation: 'NSH', logo: '', colors: { primary: '#FFB81C', secondary: '#041E42' } },
    { id: 'stl', name: 'St. Louis Blues', abbreviation: 'STL', logo: '', colors: { primary: '#002F87', secondary: '#FCB514' } },
    { id: 'wpg', name: 'Winnipeg Jets', abbreviation: 'WPG', logo: '', colors: { primary: '#041E42', secondary: '#004C97' } },
    // Pacific Division
    { id: 'ana', name: 'Anaheim Ducks', abbreviation: 'ANA', logo: '', colors: { primary: '#F47A38', secondary: '#B9975B' } },
    { id: 'cgy', name: 'Calgary Flames', abbreviation: 'CGY', logo: '', colors: { primary: '#C8102E', secondary: '#F1BE48' } },
    { id: 'edm', name: 'Edmonton Oilers', abbreviation: 'EDM', logo: '', colors: { primary: '#041E42', secondary: '#FF4C00' } },
    { id: 'lak', name: 'Los Angeles Kings', abbreviation: 'LAK', logo: '', colors: { primary: '#111111', secondary: '#A2AAAD' } },
    { id: 'sjs', name: 'San Jose Sharks', abbreviation: 'SJS', logo: '', colors: { primary: '#006D75', secondary: '#EA7200' } },
    { id: 'sea', name: 'Seattle Kraken', abbreviation: 'SEA', logo: '', colors: { primary: '#001628', secondary: '#99D9D9' } },
    { id: 'vgk', name: 'Vegas Golden Knights', abbreviation: 'VGK', logo: '', colors: { primary: '#B4975A', secondary: '#333F42' } },
    { id: 'van', name: 'Vancouver Canucks', abbreviation: 'VAN', logo: '', colors: { primary: '#00205B', secondary: '#00843D' } },
  ];
}

