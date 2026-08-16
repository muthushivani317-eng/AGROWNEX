# Crop-ID pipeline access policy

The controlled endpoint is
`POST /api/v1/crop-identity/predict-controlled`. Authentication and centralized
tester authorization execute before upload decoding.

Only Banana, Paddy, Cotton, and Groundnut can reach dispatch. Crop-ID runtime
failure, integrity failure, abstention, crop mismatch, unsupported crop,
corrupt input, and image-quality rejection prevent disease dispatch. Chilli,
Redgram, and Coconut remain disabled.

No independent semantic plant/non-plant detector has been proven; the endpoint
does not claim that capability. General farmer inference remains unauthorized.
