### Running lws minimal secure streams static policy client

This snippet shows how to execute the compiled `lws-minimal-secure-streams-staticpolicy` client. It also includes example output demonstrating the client's connection, data reception, and disconnection process, highlighting the use of a static secure streams policy and various debug messages.

```Shell
$ ./lws-minimal-secure-streams-staticpolicy
[2020/03/26 15:49:12:6640] U: LWS secure streams static policy test client [-d<verb>]
[2020/03/26 15:49:12:7067] N: lws_create_context: using ss proxy bind '(null)', port 0, ads '(null)'
[2020/03/26 15:49:12:7567] N: lws_tls_client_create_vhost_context: using mem client CA cert 914
[2020/03/26 15:49:12:7597] N: lws_tls_client_create_vhost_context: using mem client CA cert 1011
[2020/03/26 15:49:12:7603] N: lws_tls_client_create_vhost_context: using mem client CA cert 1425
[2020/03/26 15:49:12:7605] N: lws_tls_client_create_vhost_context: using mem client CA cert 1011
[2020/03/26 15:49:12:9713] N: lws_system_cpd_set: setting CPD result OK
[2020/03/26 15:49:13:9625] N: ss_api_amazon_auth_rx: acquired 588-byte api.amazon.com auth token, exp 3600s
[2020/03/26 15:49:13:9747] U: myss_state: LWSSSCS_CREATING, ord 0x0
[2020/03/26 15:49:13:9774] U: myss_state: LWSSSCS_CONNECTING, ord 0x0
[2020/03/26 15:49:14:1897] U: myss_state: LWSSSCS_CONNECTED, ord 0x0
[2020/03/26 15:49:14:1926] U: myss_rx: len 1520, flags: 1
[2020/03/26 15:49:14:1945] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:1946] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:1947] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:1948] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:1949] U: myss_rx: len 583, flags: 0
[2020/03/26 15:49:14:2087] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2089] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2090] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2091] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2092] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2093] U: myss_rx: len 583, flags: 0
[2020/03/26 15:49:14:2109] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2110] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2111] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2112] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2113] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2114] U: myss_rx: len 583, flags: 0
[2020/03/26 15:49:14:2135] U: myss_rx: len 1520, flags: 0
[2020/03/26 15:49:14:2136] U: myss_rx: len 1358, flags: 0
[2020/03/26 15:49:14:2136] U: myss_rx: len 0, flags: 2
[2020/03/26 15:49:14:2138] U: myss_state: LWSSSCS_QOS_ACK_REMOTE, ord 0x0
[2020/03/26 15:49:14:2139] N: myss_state: LWSSSCS_QOS_ACK_REMOTE
[2020/03/26 15:49:14:2170] U: myss_state: LWSSSCS_DISCONNECTED, ord 0x0
[2020/03/26 15:49:14:2192] U: myss_state: LWSSSCS_DESTROYING, ord 0x0
[2020/03/26 15:49:14:2265] E: lws_context_destroy3
[2020/03/26 15:49:14:2282] U: Completed: OK
```

### Running Autobahn Test Suite for libwebsockets

This command executes the `autobahn-test.sh` script located in the `scripts` directory, which initiates the Autobahn Test Suite against the built `libwebsockets` components.

```Shell
../scripts/autobahn-test.sh
```

### Running libwebsockets Test Server with SSL/WSS (Shell)

This command starts the `libwebsockets-test-server` with SSL/WSS (WebSocket Secure) enabled. This allows the server to handle secure WebSocket connections, typically over HTTPS.

```Shell
libwebsockets-test-server --ssl
```

### Building lws minimal secure streams static policy with CMake

This snippet provides the commands to compile the `lws-minimal-secure-streams-staticpolicy` application using CMake and Make. It sets up the build environment and then compiles the source code, preparing the executable for use.

```Shell
$ cmake . && make
```

### Running lws-minimal-http-client and Observing Output

This command executes the compiled `lws-minimal-http-client` application without any specific options, connecting to the default server (warmcat.com). The accompanying output demonstrates the client's connection lifecycle, including SSL context creation, connection attempts, and data reception, providing insight into its operational flow.

```Shell
$ ./lws-minimal-http-client
```

### Building libwebsockets for Autobahn Test Suite

This command configures and builds `libwebsockets` from the build directory, enabling extensions (`-DLWS_WITHOUT_EXTENSIONS=0`) and minimal examples (`-DLWS_WITH_MINIMAL_EXAMPLES=1`), which are prerequisites for running the Autobahn Test Suite.

```Shell
$ cmake .. -DLWS_WITHOUT_EXTENSIONS=0 -DLWS_WITH_MINIMAL_EXAMPLES=1 && make
```

### Example Output of LWS GTK HTTP Client

This snippet shows the console output when running the minimal HTTP client. It demonstrates the connection to warmcat.com, the successful HTTP 200 response, and the subsequent data reception in chunks, concluding with the 'Hello World' content received from the server.

```Shell
$
t1_main: started
[2020/02/08 18:04:07:6647] N: Loading client CA for verification ./warmcat.com.cer
[2020/02/08 18:04:07:7744] U: Connected to 46.105.127.147, http response: 200
[2020/02/08 18:04:07:7762] U: RECEIVE_CLIENT_HTTP_READ: read 4087
[2020/02/08 18:04:07:7762] U: RECEIVE_CLIENT_HTTP_READ: read 4096
[2020/02/08 18:04:07:7928] U: RECEIVE_CLIENT_HTTP_READ: read 4087
[2020/02/08 18:04:07:7929] U: RECEIVE_CLIENT_HTTP_READ: read 4096
[2020/02/08 18:04:07:7956] U: RECEIVE_CLIENT_HTTP_READ: read 4087
[2020/02/08 18:04:07:7956] U: RECEIVE_CLIENT_HTTP_READ: read 4096
[2020/02/08 18:04:07:7956] U: RECEIVE_CLIENT_HTTP_READ: read 1971
[2020/02/08 18:04:07:7956] U: LWS_CALLBACK_COMPLETED_CLIENT_HTTP
Hello World
$
```

### Running libwebsockets Fraggle Test App (Shell)

This command starts the `libwebsockets-test-fraggle` application. By default, this test application runs in server mode, demonstrating its specific functionality within the libwebsockets test suite.

```Shell
libwebsockets-test-fraggle
```

### Stopping libwebsockets Test Server Daemon (Shell)

This shell command stops a running `libwebsockets-test-server` daemon. It retrieves the process ID (PID) from the `/tmp/.lwsts-lock` file and then uses the `kill` command to terminate the process.

```Shell
kill \`cat /tmp/.lwsts-lock\`
```

### Example JSON Policy Configuration

This snippet provides a comprehensive example of a JSON policy database, illustrating the structure and typical values for various configuration sections such as release, product, schema version, retry mechanisms, certificates, trust stores, and stream definitions. It demonstrates how different components like backoff strategies, TLS settings, and authentication schemes are integrated.

```JSON
{
	"release": "01234567",
	"product": "myproduct",
	"schema-version": 1,
	"retry": [{
		"default": {
			"backoff": [1000, 2000, 3000, 5000, 10000],
			"conceal": 5,
			"jitterpc": 20
		}
	}],
	"certs": [{
		"isrg_root_x1": "MIIFazCCA1OgAw...AnX5iItreGCc="
	}, {
		"LEX3_isrg_root_x1": "MIIFjTCCA3WgAwIB...WEsikxqEt"
	}],
	"trust_stores": [{
		"le_via_isrg": ["isrg_root_x1", "LEX3_isrg_root_x1"]
	}],
	"s": [{
		"mintest": {
			"endpoint": "warmcat.com",
			"port": 4443,
			"protocol": "h1get",
			"aux": "index.html",
			"plugins": [],
			"tls": true,
			"opportunistic": true,
			"retry": "default",
			"tls_trust_store": "le_via_isrg"
		}
	}]
}
```