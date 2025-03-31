# Mega Service New

## Lessons Learned

### vLLM Docker Image Availability for ARM

1. **No ARM Support (March 2024)**
   - vLLM does not provide Docker images for ARM architecture (M1/M2 Macs)
   - Attempted images that failed:
     ```yaml
     image: vllm/vllm:latest
     image: ghcr.io/vllm-project/vllm:latest
     ```

2. **Alternative Solutions**
   - Use Hugging Face's Text Generation Inference (TGI) which has ARM support
   - Build vLLM from source for ARM
   - Use x86 emulation (not recommended due to performance impact)

3. **Documentation Gap**
   - Limited documentation about ARM compatibility
   - No clear roadmap for ARM support
   - Community discussions suggest this is a common issue

4. **Impact**
   - Development on M1/M2 Macs requires alternative solutions
   - Production deployments should consider x86 environments