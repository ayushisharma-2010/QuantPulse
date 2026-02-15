"""
One-time script: Convert the Keras 2 .h5 model to Keras 3 format.

Run this ONCE locally, then re-upload to Hugging Face:
    python convert_model.py
"""
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf
print(f"TensorFlow version: {tf.__version__}")
print(f"Keras version: {tf.keras.__version__}")

# Step 1: Load the old .h5 model (Keras 2 format)
print("\n📥 Loading old model (models/universal_lstm.h5)...")
try:
    model = tf.keras.models.load_model("models/universal_lstm.h5", compile=False)
    print(f"✅ Loaded successfully! Input shape: {model.input_shape}")
except Exception as e:
    print(f"❌ Failed to load with current Keras: {e}")
    print("\nTrying with legacy Keras...")
    os.environ["TF_USE_LEGACY_KERAS"] = "1"
    # Need to restart the TF import — run this script with TF_USE_LEGACY_KERAS=1 set
    print("Run this instead:")
    print("  set TF_USE_LEGACY_KERAS=1 && python convert_model.py")
    exit(1)

# Step 2: Print model summary
print("\n📋 Model Architecture:")
model.summary()

# Step 3: Save in new Keras 3 format (.keras)
new_path = "models/universal_lstm.keras"
print(f"\n💾 Saving in Keras 3 format → {new_path}")
model.save(new_path)
print(f"✅ Saved! New file: {new_path}")

# Step 4: Verify the new model loads correctly
print("\n🔍 Verifying new model loads...")
model2 = tf.keras.models.load_model(new_path, compile=False)
print(f"✅ Verified! Input shape: {model2.input_shape}")

print("\n" + "="*60)
print("✅ DONE! Now upload to Hugging Face:")
print("   huggingface-cli upload joy1511/QuantPulse-Models models/universal_lstm.keras universal_lstm.keras")
print("="*60)
