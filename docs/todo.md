# Todo

* Multiple auth adapters can (and are allowed to match a url). Example is https://auth.vklass.se/organisation/189 and https://auth.vklass.se/organisation/190. These url's are needed as starting points for the flow since the 189 and 190 org parameters must originate here.<br>However on that page, two different login options are presented, to that url is not deterministic.
The `ADAPTER_DESCRIPTION` was added to the adapter files to address this. We must:
* vklassgateway.py: implement a match-all adapter function
* config_flow.py: If multiple results are returned for the url, display a selection dropdown so user can manually choose the login method. That implies also saving the adapter module name to config for each device, and loading adapter based on that config. 

