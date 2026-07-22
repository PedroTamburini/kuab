const API_BASE_URL = 'http://localhost:8000/api';

export const fetchModels = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/models`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data.models || [];
    } catch (error) {
        console.error("Failed to fetch models:", error);
        throw error;
    }
};

export const chatStream = async (model, messages, onChunk, onError, onComplete) => {
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ model, messages }),
        });

        if (!response.ok) {
            const error = await response.json();
            onError(error.detail || "Server error");
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n').filter(line => line.trim() !== '');
            
            for (const line of lines) {
                try {
                    const data = JSON.parse(line);
                    if (data.error) {
                        onError(data.error);
                    } else if (data.message && data.message.content) {
                        onChunk(data.message.content);
                    }
                } catch (e) {
                    console.error("Error parsing NDJSON line:", line, e);
                }
            }
        }
        onComplete();
    } catch (error) {
        onError("Failed to connect to chat API.");
    }
};
