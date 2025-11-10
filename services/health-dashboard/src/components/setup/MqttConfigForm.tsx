import React, { useCallback, useEffect, useMemo, useState } from 'react';

type FormState = {
  brokerUrl: string;
  username: string;
  password: string;
  baseTopic: string;
};

type LoadState = 'idle' | 'loading' | 'error' | 'success';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8003';
const CONFIG_ENDPOINT = `${API_BASE_URL}/api/v1/config/integrations/mqtt`;

export const MqttConfigForm: React.FC = () => {
  const [formState, setFormState] = useState<FormState>({
    brokerUrl: '',
    username: '',
    password: '',
    baseTopic: 'zigbee2mqtt',
  });
  const [loadingState, setLoadingState] = useState<LoadState>('idle');
  const [savingState, setSavingState] = useState<LoadState>('idle');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const hasChanges = useMemo(() => savingState === 'success', [savingState]);

  const loadConfig = useCallback(async () => {
    setLoadingState('loading');
    setStatusMessage(null);

    try {
      const response = await fetch(CONFIG_ENDPOINT, { credentials: 'include' });
      if (!response.ok) {
        throw new Error(`Failed to load configuration (HTTP ${response.status})`);
      }

      const data = await response.json();

      setFormState({
        brokerUrl: data.MQTT_BROKER ?? '',
        username: data.MQTT_USERNAME ?? '',
        password: data.MQTT_PASSWORD ?? '',
        baseTopic: data.ZIGBEE2MQTT_BASE_TOPIC ?? 'zigbee2mqtt',
      });
      setLoadingState('success');
    } catch (error) {
      console.error('Failed to load MQTT configuration', error);
      setStatusMessage(
        error instanceof Error ? error.message : 'Unable to load MQTT configuration.'
      );
      setLoadingState('error');
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleChange = (field: keyof FormState) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingState('loading');
    setStatusMessage(null);

    const payload = {
      MQTT_BROKER: formState.brokerUrl.trim(),
      MQTT_USERNAME: formState.username.trim() || null,
      MQTT_PASSWORD: formState.password.trim() || null,
      ZIGBEE2MQTT_BASE_TOPIC: formState.baseTopic.trim(),
    };

    try {
      const response = await fetch(CONFIG_ENDPOINT, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        const message =
          errorPayload?.detail ??
          `Failed to save configuration (HTTP ${response.status}). Please check your values and try again.`;
        throw new Error(message);
      }

      setSavingState('success');
      setStatusMessage('Configuration saved. Restart device-intelligence-service to apply changes.');
    } catch (error) {
      console.error('Failed to save MQTT configuration', error);
      setSavingState('error');
      setStatusMessage(
        error instanceof Error
          ? error.message
          : 'Failed to save configuration. Please try again.'
      );
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          MQTT & Zigbee Connectivity
        </h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Provide the connection details for your MQTT broker and Zigbee2MQTT topic. These settings
          feed the device-intelligence service so it can subscribe to Zigbee updates.
        </p>
      </div>

      {loadingState === 'loading' ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading configuration…</p>
      ) : null}

      {statusMessage ? (
        <div
          className={`rounded-md p-3 text-sm ${
            savingState === 'error' || loadingState === 'error'
              ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-200'
              : 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-200'
          }`}
        >
          {statusMessage}
        </div>
      ) : null}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label
            htmlFor="mqtt-broker"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            MQTT Broker URL
          </label>
          <input
            id="mqtt-broker"
            type="text"
            required
            value={formState.brokerUrl}
            onChange={handleChange('brokerUrl')}
            placeholder="mqtt://192.168.1.100:1883"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Supported schemes: mqtt://, mqtts://, ws://, wss://
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label
              htmlFor="mqtt-username"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              MQTT Username
            </label>
            <input
              id="mqtt-username"
              type="text"
              value={formState.username}
              onChange={handleChange('username')}
              placeholder="homeassistant"
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label
              htmlFor="mqtt-password"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              MQTT Password
            </label>
            <input
              id="mqtt-password"
              type="password"
              value={formState.password}
              onChange={handleChange('password')}
              placeholder="••••••••"
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="zigbee-base-topic"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Zigbee2MQTT Base Topic
          </label>
          <input
            id="zigbee-base-topic"
            type="text"
            required
            value={formState.baseTopic}
            onChange={handleChange('baseTopic')}
            placeholder="zigbee2mqtt"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="submit"
            disabled={savingState === 'loading'}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
          >
            {savingState === 'loading' ? 'Saving…' : 'Save Configuration'}
          </button>
          {hasChanges ? (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Restart <code className="font-mono">device-intelligence-service</code> to apply
              changes.
            </p>
          ) : null}
        </div>
      </form>
    </div>
  );
};

