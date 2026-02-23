### Extending Base Feature Class for Specific Features in Javascript

These classes extend the base feature class (b) to implement specific features like session replay, page visibility, and others. Each class sets its feature name and initializes the aggregator. They demonstrate inheritance and feature-specific configurations.

```javascript
class A extends b{
  static featureName=y.t;
  constructor(e,t){
    let r=!(arguments.length>2&&void 0!==arguments[2])||arguments[2];
    super(e,t,y.t,r),
    this.importAggregator()
  }
}
class C extends b{
  static featureName=D.t;
  constructor(e,t){
    let r=!(arguments.length>2&&void 0!==arguments[2])||arguments[2];
    super(e,t,D.t,r),
    p.il&&((0,O.N)((()=>(0,N.p)("docHidden",[(0,P.z)()],void 0,D.t,this.ee)),!0),(0,I.bP)("pagehide",(()=>(0,N.p)("winPagehide",[(0,P.z)()],void 0,D.t,this.ee))),this.importAggregator()}}
class k extends b{
  static featureName=j.t9;
  constructor(e,t){
    let r=!(arguments.length>2&&void 0!==arguments[2])||arguments[2];
    super(e,t,j.t9,r),
    this.importAggregator()
  }
}
class B extends b{
  static featureName=L.t;
  #r=!1;
  constructor(e,r){
    let n=!(arguments.length>2&&void 0!==arguments[2])||arguments[2];
    super(e,r,L.t,n);
    try{
      this.removeOnAbort=new AbortController
    }catch(e){}
    this.ee.on("internal-error",(e=>{
      this.#r||(this.#r=!0,this.ee.emit("error",e,void 0,void 0,!1,{
        propagation: !0
      }))
    })),this.ee.on("fn-err",(e=>{
      this.#r||(this.#r=!0,this.ee.emit("error",e,void 0,void 0,!1,{
        propagation: !0
      }))
    })),this.ee.on("err",(e=>{
      this.#r||(this.#r=!0,this.ee.emit("error",e,void 0,void 0,!1,{
        propagation: !0
      }))
    })),this.ee.on("console-error",(e=>{
      this.#r||(this.#r=!0,this.ee.emit("error",e.message,void 0,void 0,!1,{
        propagation: !0
      }))
    })),this.ee.on("hub",(e=>{
      e.on("error",(e=>{
        this.#r||(this.#r=!0,this.ee.emit("error",e,void 0,void 0,!1,{
          propagation: !0
        }))
      }))
    }))
  }
}
```

### Instrument Promise API

This code instruments the native Promise object to capture and propagate execution details. It intercepts Promise creation, resolution, and rejection, emitting events like 'propagate' to track promise chaining and status. It modifies `Promise.prototype.then` to enable this instrumentation.

```javascript
const H={};function M(e){const t=function(e){return(e||n.ee).get("promise")}(e);if(H[t.debugId])return t;H[t.debugId]=!0;var r=t.context,i=c(t),a=f._A.Promise;return a&&function(){function e(r){var n=t.context(),o=i(r,"executor-",n,null,!1);const s=Reflect.construct(a,[o],e);return t.context(s).getCtx=function(){return n},s}f._A.Promise=e,Object.defineProperty(e,"name",{value:"Promise"}),e.toString=function(){return a.toString()},Object.setPrototypeOf(e,a),[ "all","race"].forEach((function(r){const n=a[r];e[r]=function(e){let i=!1;[...e||[]].forEach((e=>{this.resolve(e).then(a("all"===r),a(!1))}));const o=n.apply(this,arguments);return o;function a(e){return function(){t.emit("propagate",[null,!i],o,!1,!1),i=i||!e}}}})),["resolve","reject"].forEach((function(r){const n=a[r];e[r]=function(e){const r=n.apply(this,arguments);return e!==r&&t.emit("propagate",[e,!0],r,!1,!1),r}})),e.prototype=a.prototype;const n=a.prototype.then;a.prototype.then=function(){var e=this,o=r(e);o.promise=e;for(var a=arguments.length,s=new Array(a),c=0;c<a;c++)s[c]=arguments[c];s[0]=i(s[0],"cb-",o,null,!1),s[1]=i(s[1],"cb-",o,null,!1);const u=n.apply(this,s);return o.nextPromise=u,t.emit("propagate",[e,!0],u,!1,!1),u},a.prototype.then[o]=n,t.on("executor-start",(function(e){e[0]=i(e[0],"resolve-",this,null,!1),e[1]=i(e[1],"resolve-",this,null,!1)})),t.on("executor-err",(function(e,t,r){e[1](r)})),t.on("cb-end",(function(e,r,n){t.emit("propagate",[n,!0],this.nextPromise,!1,!1)})),t.on("propagate",(function(e,r,n){this.getCtx&&!r||(this.getCtx=function(){if(e instanceof Promise)var r=t.context(e);return r&&r.getCtx?r.getCtx():this})}))}(),t}
```

### Agent and Feature Management Class

A base class for managing agent functionalities and feature configurations. It initializes with agent identifier, aggregator, and feature name, and provides a mechanism to block features if necessary.

```javascript
r.d(t,{W:()=>i});var n=r(8325);class i{constructor(e,t,r){this.agentIdentifier=e,this.aggregator=t,this.ee=n.ee.get(e),this.featureName=r,this.blocked=!1}}
```

### Data Aggregation Class in Javascript

This class extends another class and provides methods for storing, merging, and retrieving aggregated data. It uses buckets to organize metrics and supports custom parameters. The class includes functions for calculating and storing statistical data like min, max, sum, and sum of squares.

```javascript
class _ extends w.w{
  constructor(e){
    super(e),
    this.aggregatedData={}
  }
  store(e,t,r,n,i){
    var o=this.getBucket(e,t,r,i);
    return o.metrics=function(e,t){
      t||(t={count:0});
      return t.count+=1,(0,E.D)(e,(function(e,r){
        t[e]=x(r,t[e])
      })),t}(n,o.metrics),o
  }
  merge(e,t,r,n,i){
    var o=this.getBucket(e,t,n,i);
    if(o.metrics){
      var a=o.metrics;
      a.count+=r.count,(0,E.D)(r,(function(e,t){
        if("count"!==e){
          var n=a[e],
          i=r[e];
          i&&!i.c?a[e]=x(i.t,n):a[e]=function(e,t){
            if(!t)return e;
            t.c||(t=R(t.t));
            return t.min=Math.min(e.min,t.min),t.max=Math.max(e.max,t.max),t.t+=e.t,t.sos+=e.sos,t.c+=e.c,t}(i,a[e])
        }
      }))
    }else o.metrics=r
  }
  storeMetric(e,t,r,n){
    var i=this.getBucket(e,t,r);
    return i.stats=x(n,i.stats),i
  }
  getBucket(e,t,r,n){
    this.aggregatedData[e]||(this.aggregatedData[e]={});
    var i=this.aggregatedData[e][t];
    return i||(i=this.aggregatedData[e][t]={params:r||{}},n&&(i.custom=n)),i
  }
  get(e,t){
    return t?this.aggregatedData[e]&&this.aggregatedData[e][t]:this.aggregatedData[e]
  }
  take(e){
    for(var t={},
    r="",
    n=!1,
    i=0;i<e.length;i++)t[r=e[i]]=Object.values(this.aggregatedData[r]||{}),t[r].length&&(n=!0),delete this.aggregatedData[r];
    return n?t:null
  }
}
function x(e,t){
  return null==e?function(e){
    e?e.c++:e={c:1};
    return e}(t):t?(t.c||(t=R(t.t)),t.c+=1,t.t+=e,t.sos+=e*e,e>t.max&&(t.max=e),e<t.min&&(t.min=e),t):{t:e}
}
function R(e){
  return{t:e,min:e,max:e,sos:e*e,c:1}
}
```

### Session Replay Initialization and Management

Manages session replay functionality, including loading replay configuration from local storage, initializing replay mode, and handling the 'recordReplay' event to potentially start replay. It also imports an aggregator.

```javascript
class me extends b{static featureName=t.t9;#i;constructor(e,r){let n,i=!(arguments.length>2&&void 0!==arguments[2])||arguments[2];super(e,r,t.t9,i),this.replayRunning=!1;try{n=JSON.parse(localStorage.getItem("".concat(ge.Bq,"_").concat(ge.K4)))}catch(e){}(0,g.Rc)(e)&&this.ee.on("recordReplay",(()=>this.#o())),this.#a(n)?(this.#i=n?.sessionReplayMode,this.#s()):this.importAggregator(),this.ee.on("err",(e=>{
```

### List Available Output Fields in httpx

This command displays all the available fields that can be included in the output of an httpx scan. This helps users understand the data points they can extract and customize their scans accordingly.

```bash
# List available output fields
httpx -list-output-fields
# Output: url, status_code, content_length, title, webserver, tech, etc.
```

### Session Replay Configuration and Constants

Configures and defines constants for session replay functionality. It includes settings for replay recording, pausing, running states, and error handling, along with various timing and size limits for replay data.

```javascript
r.d(t,{Ef:()=>o,J0:()=>f,Mi:()=>l,Vb:()=>a,Ye:()=>c,fm:()=>u,i9:()=>s,pB:()=>h,t9:()=>i,u0:()=>d});var n=r(7056);const i=r(3325).D.sessionReplay,o={RECORD:"recordReplay",PAUSE:"pauseReplay",REPLAY_RUNNING:"replayRunning",ERROR_DURING_REPLAY:"errorDuringReplay"},a=.12,s={DomContentLoaded:0,Load:1,FullSnapshot:2,IncrementalSnapshot:3,Meta:4,Custom:5},c=1e6,u=64e3,d={[n.IK.ERROR]:15e3,[n.IK.FULL]:3e5,[n.IK.OFF]:0},l={RESET:{message:"Session was reset",sm:"Reset"},IMPORT:{message:"Recorder failed to import",sm:"Import"},TOO_MANY:{message:"429: Too Many Requests",sm:"Too-Many"},TOO_BIG:{message:"Payload was too large",sm:"Too-Big"},CROSS_TAB:{message:"Session Entity was set to OFF on another tab",sm:"Cross-Tab"},ENTITLEMENTS:{message:"Session Replay is not allowed and will not be started",sm:"Entitlement"}},f=5e3,h={API:"api"}}
```

### Interaction and Event Type Constants

Defines constants for different types of interactions and events, including click, keydown, submit, AJAX, and SPA navigation. It also defines states for in-progress, finished, and cancelled operations.

```javascript
r.d(t,{K8:()=>s,QZ:()=>c,cS:()=>o,sE:()=>i,t9:()=>a,vh:()=>u});var n=r(3325);const i=["click","keydown","submit"],o="api",a=n.D.softNav,s={INITIAL_PAGE_LOAD:"",ROUTE_CHANGE:1,UNSPECIFIED:2},c={INTERACTION:1,AJAX:2,CUSTOM_END:3,CUSTOM_TRACER:4},u={IP:"in progress",FIN:"finished",CAN:"cancelled"}}
```

### Monitor DOM Mutations with MutationObserver

This snippet enhances the MutationObserver API to enable monitoring of DOM changes. It replaces the native MutationObserver with a wrapped version that allows for event emission upon observer initialization, facilitating the tracking of DOM manipulation activities. It relies on the existence of `MutationObserver` in the browser's `window.MutationObserver`.

```javascript
const k={};function L(e){const t=function(e){return(e||n.ee).get("mutation")}(e);if(!f.il||k[t.debugId])return t;k[t.debugId]=!0;var r=c(t),i=f._A.MutationObserver;return i&&(window.MutationObserver=function(e){return this instanceof i?new i(r(e,"fn- ")):i.apply(this,arguments)},MutationObserver.prototype=i.prototype),t}
```

### Initialize Agent Features in JavaScript

Initializes the main agent with a shared aggregator and desired features. It handles feature dependencies, sorts them by priority, and initializes each feature class. Includes error handling for initialization failures and cleanup of initialized agents.

```javascript
new class extends o {
  constructor(t, r) {
    super(r), p._A ? (this.sharedAggregator = new _({ agentIdentifier: this.agentIdentifier }), this.features = {}, (0, S.h5)(this.agentIdentifier, this), this.desiredFeatures = new Set(t.features || []), this.desiredFeatures.add(A), this.runSoftNavOverSpa = [...this.desiredFeatures].some((e => e.featureName === a.D.softNav)), (0, d.j)(this, t, t.loaderType || 'agent'), this.run()) : (0, e.Z)('Failed to initialize the agent. Could not determine the runtime environment.');
  }
  get config() {
    return { info: this.info, init: this.init, loader_config: this.loader_config, runtime: this.runtime };
  }
  run() {
    try {
      const t = u(this.agentIdentifier), r = [...this.desiredFeatures];
      r.sort(((e, t) => a.p[e.featureName] - a.p[t.featureName]));
      r.forEach((r => {
        if (!t[r.featureName] && r.featureName !== a.D.pageViewEvent) return;
        if (this.runSoftNavOverSpa && r.featureName === a.D.spa) return;
        if (!this.runSoftNavOverSpa && r.featureName === a.D.softNav) return;
        const n = (() => {
          switch (e) {
            case a.D.ajax: return [a.D.jserrors];
            case a.D.sessionTrace: return [a.D.ajax, a.D.pageViewEvent];
            case a.D.sessionReplay: return [a.D.sessionTrace];
            case a.D.pageViewTiming: return [a.D.pageViewEvent];
            default: return [];
          }
        })(r.featureName);
        n.every((e => e in this.features)) || (0, e.Z)(''.concat(r.featureName, ' is enabled but one or more dependent features has not been initialized (').concat((0, T.P)(n), '). This may cause unintended consequences or missing data...'));
        this.features[r.featureName] = new r(this.agentIdentifier, this.sharedAggregator);
      }));
    } catch (t) {
      (0, e.Z)('Failed to initialize all enabled instrument classes (agent aborted) -', t);
      for (const e in this.features) this.features[e].abortHandler?.();
      const r = (0, S.fP)();
      delete r.initializedAgents[this.agentIdentifier]?.api, delete r.initializedAgents[this.agentIdentifier]?.features, delete this.sharedAggregator;
      return r.ee.get(this.agentIdentifier).abort(), !1;
    }
  }
}
```