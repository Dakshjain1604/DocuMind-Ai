/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "app/api/auth/signin/route";
exports.ids = ["app/api/auth/signin/route"];
exports.modules = {

/***/ "(rsc)/./app/api/auth/signin/route.ts":
/*!**************************************!*\
  !*** ./app/api/auth/signin/route.ts ***!
  \**************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   POST: () => (/* binding */ POST)\n/* harmony export */ });\n/* harmony import */ var next_server__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/server */ \"(rsc)/./node_modules/next/dist/api/server.js\");\n/* harmony import */ var bcryptjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! bcryptjs */ \"(rsc)/./node_modules/bcryptjs/index.js\");\n/* harmony import */ var jsonwebtoken__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! jsonwebtoken */ \"(rsc)/./node_modules/jsonwebtoken/index.js\");\n/* harmony import */ var jsonwebtoken__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(jsonwebtoken__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _lib_mongodb__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @/lib/mongodb */ \"(rsc)/./lib/mongodb.ts\");\n/* harmony import */ var _models_userModel__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! @/models/userModel */ \"(rsc)/./models/userModel.ts\");\n// app/api/auth/signin/route.ts\n\n\n\n\n\nconst JWT_SECRET = process.env.JWT_SECRET || \"changeme\";\nasync function POST(req) {\n    await (0,_lib_mongodb__WEBPACK_IMPORTED_MODULE_3__.connectToMongoDB)();\n    try {\n        const { email, password } = await req.json();\n        console.log(email, password);\n        if (!email || !password) {\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                message: \"Email and password are required.\"\n            }, {\n                status: 400\n            });\n        }\n        const user = await _models_userModel__WEBPACK_IMPORTED_MODULE_4__[\"default\"].findOne({\n            email\n        });\n        console.log(user);\n        if (!user) {\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                message: \"Invalid credentials.\"\n            }, {\n                status: 401\n            });\n        }\n        const isPasswordCorrect = await bcryptjs__WEBPACK_IMPORTED_MODULE_1__[\"default\"].compare(password, user.password);\n        if (!isPasswordCorrect) {\n            return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n                message: \"Invalid credentials.\"\n            }, {\n                status: 401\n            });\n        }\n        const token = jsonwebtoken__WEBPACK_IMPORTED_MODULE_2___default().sign({\n            id: user._id,\n            email: user.email\n        }, JWT_SECRET, {\n            expiresIn: \"7d\"\n        });\n        const res = next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n            message: \"Signin successful.\"\n        });\n        res.cookies.set(\"token\", token, {\n            httpOnly: true,\n            path: \"/\",\n            maxAge: 60 * 60 * 1,\n            secure: true,\n            sameSite: \"none\"\n        });\n        return res;\n    } catch (error) {\n        console.error(\"Signin error:\", error);\n        return next_server__WEBPACK_IMPORTED_MODULE_0__.NextResponse.json({\n            message: \"Internal server error.\"\n        }, {\n            status: 500\n        });\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9hcHAvYXBpL2F1dGgvc2lnbmluL3JvdXRlLnRzIiwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7QUFBQSwrQkFBK0I7QUFDeUI7QUFDMUI7QUFDQztBQUNrQjtBQUNYO0FBQ3RDLE1BQU1LLGFBQVdDLFFBQVFDLEdBQUcsQ0FBQ0YsVUFBVSxJQUFJO0FBQ3BDLGVBQWVHLEtBQUtDLEdBQWdCO0lBQ3pDLE1BQU1OLDhEQUFnQkE7SUFFdEIsSUFBSTtRQUNGLE1BQU0sRUFBRU8sS0FBSyxFQUFFQyxRQUFRLEVBQUUsR0FBRyxNQUFNRixJQUFJRyxJQUFJO1FBQzFDQyxRQUFRQyxHQUFHLENBQUNKLE9BQU1DO1FBQ2xCLElBQUksQ0FBQ0QsU0FBUyxDQUFDQyxVQUFVO1lBQ3ZCLE9BQU9YLHFEQUFZQSxDQUFDWSxJQUFJLENBQ3RCO2dCQUFFRyxTQUFTO1lBQW1DLEdBQzlDO2dCQUFFQyxRQUFRO1lBQUk7UUFFbEI7UUFFQSxNQUFNQyxPQUFPLE1BQU1iLHlEQUFJQSxDQUFDYyxPQUFPLENBQUM7WUFBRVI7UUFBTTtRQUN4Q0csUUFBUUMsR0FBRyxDQUFDRztRQUNaLElBQUksQ0FBQ0EsTUFBTTtZQUNULE9BQU9qQixxREFBWUEsQ0FBQ1ksSUFBSSxDQUN0QjtnQkFBRUcsU0FBUztZQUF1QixHQUNsQztnQkFBRUMsUUFBUTtZQUFJO1FBRWxCO1FBRUEsTUFBTUcsb0JBQW9CLE1BQU1sQix3REFBYyxDQUFDVSxVQUFVTSxLQUFLTixRQUFRO1FBRXRFLElBQUksQ0FBQ1EsbUJBQW1CO1lBQ3RCLE9BQU9uQixxREFBWUEsQ0FBQ1ksSUFBSSxDQUN0QjtnQkFBRUcsU0FBUztZQUF1QixHQUNsQztnQkFBRUMsUUFBUTtZQUFJO1FBRWxCO1FBRUEsTUFBTUssUUFBUW5CLHdEQUFRLENBQUM7WUFBRXFCLElBQUlOLEtBQUtPLEdBQUc7WUFBRWQsT0FBT08sS0FBS1AsS0FBSztRQUFDLEdBQUdMLFlBQVk7WUFDdEVvQixXQUFXO1FBQ2I7UUFFQSxNQUFNQyxNQUFNMUIscURBQVlBLENBQUNZLElBQUksQ0FBQztZQUFFRyxTQUFTO1FBQXFCO1FBQzlEVyxJQUFJQyxPQUFPLENBQUNDLEdBQUcsQ0FBQyxTQUFTUCxPQUFPO1lBQzlCUSxVQUFVO1lBQ1ZDLE1BQU07WUFDTkMsUUFBUSxLQUFLLEtBQUs7WUFDbEJDLFFBQVE7WUFDUkMsVUFBVTtRQUNaO1FBQ0EsT0FBT1A7SUFDVCxFQUFFLE9BQU9RLE9BQU87UUFDZHJCLFFBQVFxQixLQUFLLENBQUMsaUJBQWlCQTtRQUMvQixPQUFPbEMscURBQVlBLENBQUNZLElBQUksQ0FDdEI7WUFBRUcsU0FBUztRQUF5QixHQUNwQztZQUFFQyxRQUFRO1FBQUk7SUFFbEI7QUFDRiIsInNvdXJjZXMiOlsiL1VzZXJzL2Rha3NoamFpbi9DT0RFUy9BSV9Eb2N4L2Zyb250ZW5kL2FwcC9hcGkvYXV0aC9zaWduaW4vcm91dGUudHMiXSwic291cmNlc0NvbnRlbnQiOlsiLy8gYXBwL2FwaS9hdXRoL3NpZ25pbi9yb3V0ZS50c1xuaW1wb3J0IHsgTmV4dFJlcXVlc3QsIE5leHRSZXNwb25zZSB9IGZyb20gXCJuZXh0L3NlcnZlclwiO1xuaW1wb3J0IGJjcnlwdCBmcm9tIFwiYmNyeXB0anNcIjtcbmltcG9ydCBqd3QgZnJvbSBcImpzb253ZWJ0b2tlblwiO1xuaW1wb3J0IHsgY29ubmVjdFRvTW9uZ29EQiB9IGZyb20gXCJAL2xpYi9tb25nb2RiXCI7XG5pbXBvcnQgVXNlciBmcm9tIFwiQC9tb2RlbHMvdXNlck1vZGVsXCI7IFxuY29uc3QgSldUX1NFQ1JFVD1wcm9jZXNzLmVudi5KV1RfU0VDUkVUIHx8IFwiY2hhbmdlbWVcIjtcbmV4cG9ydCBhc3luYyBmdW5jdGlvbiBQT1NUKHJlcTogTmV4dFJlcXVlc3QpIHtcbiAgYXdhaXQgY29ubmVjdFRvTW9uZ29EQigpO1xuXG4gIHRyeSB7XG4gICAgY29uc3QgeyBlbWFpbCwgcGFzc3dvcmQgfSA9IGF3YWl0IHJlcS5qc29uKCk7XG4gICAgY29uc29sZS5sb2coZW1haWwscGFzc3dvcmQpXG4gICAgaWYgKCFlbWFpbCB8fCAhcGFzc3dvcmQpIHtcbiAgICAgIHJldHVybiBOZXh0UmVzcG9uc2UuanNvbihcbiAgICAgICAgeyBtZXNzYWdlOiBcIkVtYWlsIGFuZCBwYXNzd29yZCBhcmUgcmVxdWlyZWQuXCIgfSxcbiAgICAgICAgeyBzdGF0dXM6IDQwMCB9XG4gICAgICApO1xuICAgIH1cblxuICAgIGNvbnN0IHVzZXIgPSBhd2FpdCBVc2VyLmZpbmRPbmUoeyBlbWFpbCB9KTtcbiAgICBjb25zb2xlLmxvZyh1c2VyKVxuICAgIGlmICghdXNlcikge1xuICAgICAgcmV0dXJuIE5leHRSZXNwb25zZS5qc29uKFxuICAgICAgICB7IG1lc3NhZ2U6IFwiSW52YWxpZCBjcmVkZW50aWFscy5cIiB9LFxuICAgICAgICB7IHN0YXR1czogNDAxIH1cbiAgICAgICk7XG4gICAgfVxuXG4gICAgY29uc3QgaXNQYXNzd29yZENvcnJlY3QgPSBhd2FpdCBiY3J5cHQuY29tcGFyZShwYXNzd29yZCwgdXNlci5wYXNzd29yZCk7XG5cbiAgICBpZiAoIWlzUGFzc3dvcmRDb3JyZWN0KSB7XG4gICAgICByZXR1cm4gTmV4dFJlc3BvbnNlLmpzb24oXG4gICAgICAgIHsgbWVzc2FnZTogXCJJbnZhbGlkIGNyZWRlbnRpYWxzLlwiIH0sXG4gICAgICAgIHsgc3RhdHVzOiA0MDEgfVxuICAgICAgKTtcbiAgICB9XG5cbiAgICBjb25zdCB0b2tlbiA9IGp3dC5zaWduKHsgaWQ6IHVzZXIuX2lkLCBlbWFpbDogdXNlci5lbWFpbCB9LCBKV1RfU0VDUkVULCB7XG4gICAgICBleHBpcmVzSW46IFwiN2RcIixcbiAgICB9KTtcblxuICAgIGNvbnN0IHJlcyA9IE5leHRSZXNwb25zZS5qc29uKHsgbWVzc2FnZTogXCJTaWduaW4gc3VjY2Vzc2Z1bC5cIiB9KTtcbiAgICByZXMuY29va2llcy5zZXQoXCJ0b2tlblwiLCB0b2tlbiwge1xuICAgICAgaHR0cE9ubHk6IHRydWUsXG4gICAgICBwYXRoOiBcIi9cIixcbiAgICAgIG1heEFnZTogNjAgKiA2MCAqIDEgLCAvLyAxIGhvdXJcbiAgICAgIHNlY3VyZTogdHJ1ZSxcbiAgICAgIHNhbWVTaXRlOiBcIm5vbmVcIixcbiAgICB9KTtcbiAgICByZXR1cm4gcmVzO1xuICB9IGNhdGNoIChlcnJvcikge1xuICAgIGNvbnNvbGUuZXJyb3IoXCJTaWduaW4gZXJyb3I6XCIsIGVycm9yKTtcbiAgICByZXR1cm4gTmV4dFJlc3BvbnNlLmpzb24oXG4gICAgICB7IG1lc3NhZ2U6IFwiSW50ZXJuYWwgc2VydmVyIGVycm9yLlwiIH0sXG4gICAgICB7IHN0YXR1czogNTAwIH1cbiAgICApO1xuICB9XG59XG4iXSwibmFtZXMiOlsiTmV4dFJlc3BvbnNlIiwiYmNyeXB0Iiwiand0IiwiY29ubmVjdFRvTW9uZ29EQiIsIlVzZXIiLCJKV1RfU0VDUkVUIiwicHJvY2VzcyIsImVudiIsIlBPU1QiLCJyZXEiLCJlbWFpbCIsInBhc3N3b3JkIiwianNvbiIsImNvbnNvbGUiLCJsb2ciLCJtZXNzYWdlIiwic3RhdHVzIiwidXNlciIsImZpbmRPbmUiLCJpc1Bhc3N3b3JkQ29ycmVjdCIsImNvbXBhcmUiLCJ0b2tlbiIsInNpZ24iLCJpZCIsIl9pZCIsImV4cGlyZXNJbiIsInJlcyIsImNvb2tpZXMiLCJzZXQiLCJodHRwT25seSIsInBhdGgiLCJtYXhBZ2UiLCJzZWN1cmUiLCJzYW1lU2l0ZSIsImVycm9yIl0sImlnbm9yZUxpc3QiOltdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(rsc)/./app/api/auth/signin/route.ts\n");

/***/ }),

/***/ "(rsc)/./lib/mongodb.ts":
/*!************************!*\
  !*** ./lib/mongodb.ts ***!
  \************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   connectToMongoDB: () => (/* binding */ connectToMongoDB)\n/* harmony export */ });\n/* harmony import */ var mongoose__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! mongoose */ \"mongoose\");\n/* harmony import */ var mongoose__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(mongoose__WEBPACK_IMPORTED_MODULE_0__);\n\nlet cachedConnection = null;\nasync function connectToMongoDB() {\n    if (cachedConnection) {\n        console.log(\"Using cached db connection\");\n        return cachedConnection;\n    }\n    try {\n        const cnx = await mongoose__WEBPACK_IMPORTED_MODULE_0___default().connect(process.env.MONGODB_URI);\n        cachedConnection = cnx.connection;\n        console.log(\"New mongodb connection established\");\n        return cachedConnection;\n    } catch (error) {\n        console.log(error);\n        throw error;\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9saWIvbW9uZ29kYi50cyIsIm1hcHBpbmdzIjoiOzs7Ozs7QUFBZ0Q7QUFHaEQsSUFBSUMsbUJBQXNDO0FBR25DLGVBQWVDO0lBRXBCLElBQUlELGtCQUFrQjtRQUNwQkUsUUFBUUMsR0FBRyxDQUFDO1FBQ1osT0FBT0g7SUFDVDtJQUNBLElBQUk7UUFFRixNQUFNSSxNQUFNLE1BQU1MLHVEQUFnQixDQUFDTyxRQUFRQyxHQUFHLENBQUNDLFdBQVc7UUFFMURSLG1CQUFtQkksSUFBSUssVUFBVTtRQUVqQ1AsUUFBUUMsR0FBRyxDQUFDO1FBRVosT0FBT0g7SUFDVCxFQUFFLE9BQU9VLE9BQU87UUFFZFIsUUFBUUMsR0FBRyxDQUFDTztRQUNaLE1BQU1BO0lBQ1I7QUFDRiIsInNvdXJjZXMiOlsiL1VzZXJzL2Rha3NoamFpbi9DT0RFUy9BSV9Eb2N4L2Zyb250ZW5kL2xpYi9tb25nb2RiLnRzIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCBtb25nb29zZSwgeyBDb25uZWN0aW9uIH0gZnJvbSBcIm1vbmdvb3NlXCI7XG5cblxubGV0IGNhY2hlZENvbm5lY3Rpb246IENvbm5lY3Rpb24gfCBudWxsID0gbnVsbDtcblxuXG5leHBvcnQgYXN5bmMgZnVuY3Rpb24gY29ubmVjdFRvTW9uZ29EQigpIHtcbiAgXG4gIGlmIChjYWNoZWRDb25uZWN0aW9uKSB7XG4gICAgY29uc29sZS5sb2coXCJVc2luZyBjYWNoZWQgZGIgY29ubmVjdGlvblwiKTtcbiAgICByZXR1cm4gY2FjaGVkQ29ubmVjdGlvbjtcbiAgfVxuICB0cnkge1xuICAgIFxuICAgIGNvbnN0IGNueCA9IGF3YWl0IG1vbmdvb3NlLmNvbm5lY3QocHJvY2Vzcy5lbnYuTU9OR09EQl9VUkkhKTtcbiAgICBcbiAgICBjYWNoZWRDb25uZWN0aW9uID0gY254LmNvbm5lY3Rpb247XG4gICAgXG4gICAgY29uc29sZS5sb2coXCJOZXcgbW9uZ29kYiBjb25uZWN0aW9uIGVzdGFibGlzaGVkXCIpO1xuICBcbiAgICByZXR1cm4gY2FjaGVkQ29ubmVjdGlvbjtcbiAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICBcbiAgICBjb25zb2xlLmxvZyhlcnJvcik7XG4gICAgdGhyb3cgZXJyb3I7XG4gIH1cbn0iXSwibmFtZXMiOlsibW9uZ29vc2UiLCJjYWNoZWRDb25uZWN0aW9uIiwiY29ubmVjdFRvTW9uZ29EQiIsImNvbnNvbGUiLCJsb2ciLCJjbngiLCJjb25uZWN0IiwicHJvY2VzcyIsImVudiIsIk1PTkdPREJfVVJJIiwiY29ubmVjdGlvbiIsImVycm9yIl0sImlnbm9yZUxpc3QiOltdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(rsc)/./lib/mongodb.ts\n");

/***/ }),

/***/ "(rsc)/./models/userModel.ts":
/*!*****************************!*\
  !*** ./models/userModel.ts ***!
  \*****************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var mongoose__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! mongoose */ \"mongoose\");\n/* harmony import */ var mongoose__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(mongoose__WEBPACK_IMPORTED_MODULE_0__);\n// lib/models/User.ts\n\nconst UserSchema = new mongoose__WEBPACK_IMPORTED_MODULE_0__.Schema({\n    name: {\n        type: String,\n        required: true\n    },\n    email: {\n        type: String,\n        required: true,\n        unique: true\n    },\n    password: {\n        type: String,\n        required: true\n    },\n    createdAt: {\n        type: Date,\n        default: Date.now\n    }\n});\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (mongoose__WEBPACK_IMPORTED_MODULE_0__.models.User || mongoose__WEBPACK_IMPORTED_MODULE_0___default().model('User', UserSchema));\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9tb2RlbHMvdXNlck1vZGVsLnRzIiwibWFwcGluZ3MiOiI7Ozs7OztBQUFBLHFCQUFxQjtBQUN5QztBQVM5RCxNQUFNRyxhQUFhLElBQUlGLDRDQUFNQSxDQUFRO0lBQ25DRyxNQUFNO1FBQUVDLE1BQU1DO1FBQVFDLFVBQVU7SUFBSztJQUNyQ0MsT0FBTztRQUFFSCxNQUFNQztRQUFRQyxVQUFVO1FBQU1FLFFBQVE7SUFBSztJQUNwREMsVUFBVTtRQUFFTCxNQUFNQztRQUFRQyxVQUFVO0lBQUs7SUFDekNJLFdBQVc7UUFBRU4sTUFBTU87UUFBTUMsU0FBU0QsS0FBS0UsR0FBRztJQUFDO0FBQzdDO0FBR0EsaUVBQWVaLDRDQUFNQSxDQUFDYSxJQUFJLElBQUlmLHFEQUFjLENBQVEsUUFBUUcsV0FBV0EsRUFBQyIsInNvdXJjZXMiOlsiL1VzZXJzL2Rha3NoamFpbi9DT0RFUy9BSV9Eb2N4L2Zyb250ZW5kL21vZGVscy91c2VyTW9kZWwudHMiXSwic291cmNlc0NvbnRlbnQiOlsiLy8gbGliL21vZGVscy9Vc2VyLnRzXG5pbXBvcnQgbW9uZ29vc2UsIHsgU2NoZW1hLCBEb2N1bWVudCwgbW9kZWxzIH0gZnJvbSAnbW9uZ29vc2UnO1xuXG5leHBvcnQgaW50ZXJmYWNlIElVc2VyIGV4dGVuZHMgRG9jdW1lbnQge1xuICBuYW1lOiBzdHJpbmc7XG4gIGVtYWlsOiBzdHJpbmc7XG4gIHBhc3N3b3JkOiBzdHJpbmc7XG4gIGNyZWF0ZWRBdDogRGF0ZTtcbn1cblxuY29uc3QgVXNlclNjaGVtYSA9IG5ldyBTY2hlbWE8SVVzZXI+KHtcbiAgbmFtZTogeyB0eXBlOiBTdHJpbmcsIHJlcXVpcmVkOiB0cnVlIH0sXG4gIGVtYWlsOiB7IHR5cGU6IFN0cmluZywgcmVxdWlyZWQ6IHRydWUsIHVuaXF1ZTogdHJ1ZSB9LFxuICBwYXNzd29yZDogeyB0eXBlOiBTdHJpbmcsIHJlcXVpcmVkOiB0cnVlIH0sXG4gIGNyZWF0ZWRBdDogeyB0eXBlOiBEYXRlLCBkZWZhdWx0OiBEYXRlLm5vdyB9LFxufSk7XG5cblxuZXhwb3J0IGRlZmF1bHQgbW9kZWxzLlVzZXIgfHwgbW9uZ29vc2UubW9kZWw8SVVzZXI+KCdVc2VyJywgVXNlclNjaGVtYSk7XG4iXSwibmFtZXMiOlsibW9uZ29vc2UiLCJTY2hlbWEiLCJtb2RlbHMiLCJVc2VyU2NoZW1hIiwibmFtZSIsInR5cGUiLCJTdHJpbmciLCJyZXF1aXJlZCIsImVtYWlsIiwidW5pcXVlIiwicGFzc3dvcmQiLCJjcmVhdGVkQXQiLCJEYXRlIiwiZGVmYXVsdCIsIm5vdyIsIlVzZXIiLCJtb2RlbCJdLCJpZ25vcmVMaXN0IjpbXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(rsc)/./models/userModel.ts\n");

/***/ }),

/***/ "(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fauth%2Fsignin%2Froute&page=%2Fapi%2Fauth%2Fsignin%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fauth%2Fsignin%2Froute.ts&appDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!":
/*!***************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fauth%2Fsignin%2Froute&page=%2Fapi%2Fauth%2Fsignin%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fauth%2Fsignin%2Froute.ts&appDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D! ***!
  \***************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   patchFetch: () => (/* binding */ patchFetch),\n/* harmony export */   routeModule: () => (/* binding */ routeModule),\n/* harmony export */   serverHooks: () => (/* binding */ serverHooks),\n/* harmony export */   workAsyncStorage: () => (/* binding */ workAsyncStorage),\n/* harmony export */   workUnitAsyncStorage: () => (/* binding */ workUnitAsyncStorage)\n/* harmony export */ });\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next/dist/server/route-modules/app-route/module.compiled */ \"(rsc)/./node_modules/next/dist/server/route-modules/app-route/module.compiled.js\");\n/* harmony import */ var next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next/dist/server/route-kind */ \"(rsc)/./node_modules/next/dist/server/route-kind.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! next/dist/server/lib/patch-fetch */ \"(rsc)/./node_modules/next/dist/server/lib/patch-fetch.js\");\n/* harmony import */ var next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _Users_dakshjain_CODES_AI_Docx_frontend_app_api_auth_signin_route_ts__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./app/api/auth/signin/route.ts */ \"(rsc)/./app/api/auth/signin/route.ts\");\n\n\n\n\n// We inject the nextConfigOutput here so that we can use them in the route\n// module.\nconst nextConfigOutput = \"\"\nconst routeModule = new next_dist_server_route_modules_app_route_module_compiled__WEBPACK_IMPORTED_MODULE_0__.AppRouteRouteModule({\n    definition: {\n        kind: next_dist_server_route_kind__WEBPACK_IMPORTED_MODULE_1__.RouteKind.APP_ROUTE,\n        page: \"/api/auth/signin/route\",\n        pathname: \"/api/auth/signin\",\n        filename: \"route\",\n        bundlePath: \"app/api/auth/signin/route\"\n    },\n    resolvedPagePath: \"/Users/dakshjain/CODES/AI_Docx/frontend/app/api/auth/signin/route.ts\",\n    nextConfigOutput,\n    userland: _Users_dakshjain_CODES_AI_Docx_frontend_app_api_auth_signin_route_ts__WEBPACK_IMPORTED_MODULE_3__\n});\n// Pull out the exports that we need to expose from the module. This should\n// be eliminated when we've moved the other routes to the new format. These\n// are used to hook into the route.\nconst { workAsyncStorage, workUnitAsyncStorage, serverHooks } = routeModule;\nfunction patchFetch() {\n    return (0,next_dist_server_lib_patch_fetch__WEBPACK_IMPORTED_MODULE_2__.patchFetch)({\n        workAsyncStorage,\n        workUnitAsyncStorage\n    });\n}\n\n\n//# sourceMappingURL=app-route.js.map//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHJzYykvLi9ub2RlX21vZHVsZXMvbmV4dC9kaXN0L2J1aWxkL3dlYnBhY2svbG9hZGVycy9uZXh0LWFwcC1sb2FkZXIvaW5kZXguanM/bmFtZT1hcHAlMkZhcGklMkZhdXRoJTJGc2lnbmluJTJGcm91dGUmcGFnZT0lMkZhcGklMkZhdXRoJTJGc2lnbmluJTJGcm91dGUmYXBwUGF0aHM9JnBhZ2VQYXRoPXByaXZhdGUtbmV4dC1hcHAtZGlyJTJGYXBpJTJGYXV0aCUyRnNpZ25pbiUyRnJvdXRlLnRzJmFwcERpcj0lMkZVc2VycyUyRmRha3NoamFpbiUyRkNPREVTJTJGQUlfRG9jeCUyRmZyb250ZW5kJTJGYXBwJnBhZ2VFeHRlbnNpb25zPXRzeCZwYWdlRXh0ZW5zaW9ucz10cyZwYWdlRXh0ZW5zaW9ucz1qc3gmcGFnZUV4dGVuc2lvbnM9anMmcm9vdERpcj0lMkZVc2VycyUyRmRha3NoamFpbiUyRkNPREVTJTJGQUlfRG9jeCUyRmZyb250ZW5kJmlzRGV2PXRydWUmdHNjb25maWdQYXRoPXRzY29uZmlnLmpzb24mYmFzZVBhdGg9JmFzc2V0UHJlZml4PSZuZXh0Q29uZmlnT3V0cHV0PSZwcmVmZXJyZWRSZWdpb249Jm1pZGRsZXdhcmVDb25maWc9ZTMwJTNEISIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7OztBQUErRjtBQUN2QztBQUNxQjtBQUNvQjtBQUNqRztBQUNBO0FBQ0E7QUFDQSx3QkFBd0IseUdBQW1CO0FBQzNDO0FBQ0EsY0FBYyxrRUFBUztBQUN2QjtBQUNBO0FBQ0E7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUNBO0FBQ0EsWUFBWTtBQUNaLENBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQSxRQUFRLHNEQUFzRDtBQUM5RDtBQUNBLFdBQVcsNEVBQVc7QUFDdEI7QUFDQTtBQUNBLEtBQUs7QUFDTDtBQUMwRjs7QUFFMUYiLCJzb3VyY2VzIjpbIiJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgeyBBcHBSb3V0ZVJvdXRlTW9kdWxlIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvcm91dGUtbW9kdWxlcy9hcHAtcm91dGUvbW9kdWxlLmNvbXBpbGVkXCI7XG5pbXBvcnQgeyBSb3V0ZUtpbmQgfSBmcm9tIFwibmV4dC9kaXN0L3NlcnZlci9yb3V0ZS1raW5kXCI7XG5pbXBvcnQgeyBwYXRjaEZldGNoIGFzIF9wYXRjaEZldGNoIH0gZnJvbSBcIm5leHQvZGlzdC9zZXJ2ZXIvbGliL3BhdGNoLWZldGNoXCI7XG5pbXBvcnQgKiBhcyB1c2VybGFuZCBmcm9tIFwiL1VzZXJzL2Rha3NoamFpbi9DT0RFUy9BSV9Eb2N4L2Zyb250ZW5kL2FwcC9hcGkvYXV0aC9zaWduaW4vcm91dGUudHNcIjtcbi8vIFdlIGluamVjdCB0aGUgbmV4dENvbmZpZ091dHB1dCBoZXJlIHNvIHRoYXQgd2UgY2FuIHVzZSB0aGVtIGluIHRoZSByb3V0ZVxuLy8gbW9kdWxlLlxuY29uc3QgbmV4dENvbmZpZ091dHB1dCA9IFwiXCJcbmNvbnN0IHJvdXRlTW9kdWxlID0gbmV3IEFwcFJvdXRlUm91dGVNb2R1bGUoe1xuICAgIGRlZmluaXRpb246IHtcbiAgICAgICAga2luZDogUm91dGVLaW5kLkFQUF9ST1VURSxcbiAgICAgICAgcGFnZTogXCIvYXBpL2F1dGgvc2lnbmluL3JvdXRlXCIsXG4gICAgICAgIHBhdGhuYW1lOiBcIi9hcGkvYXV0aC9zaWduaW5cIixcbiAgICAgICAgZmlsZW5hbWU6IFwicm91dGVcIixcbiAgICAgICAgYnVuZGxlUGF0aDogXCJhcHAvYXBpL2F1dGgvc2lnbmluL3JvdXRlXCJcbiAgICB9LFxuICAgIHJlc29sdmVkUGFnZVBhdGg6IFwiL1VzZXJzL2Rha3NoamFpbi9DT0RFUy9BSV9Eb2N4L2Zyb250ZW5kL2FwcC9hcGkvYXV0aC9zaWduaW4vcm91dGUudHNcIixcbiAgICBuZXh0Q29uZmlnT3V0cHV0LFxuICAgIHVzZXJsYW5kXG59KTtcbi8vIFB1bGwgb3V0IHRoZSBleHBvcnRzIHRoYXQgd2UgbmVlZCB0byBleHBvc2UgZnJvbSB0aGUgbW9kdWxlLiBUaGlzIHNob3VsZFxuLy8gYmUgZWxpbWluYXRlZCB3aGVuIHdlJ3ZlIG1vdmVkIHRoZSBvdGhlciByb3V0ZXMgdG8gdGhlIG5ldyBmb3JtYXQuIFRoZXNlXG4vLyBhcmUgdXNlZCB0byBob29rIGludG8gdGhlIHJvdXRlLlxuY29uc3QgeyB3b3JrQXN5bmNTdG9yYWdlLCB3b3JrVW5pdEFzeW5jU3RvcmFnZSwgc2VydmVySG9va3MgfSA9IHJvdXRlTW9kdWxlO1xuZnVuY3Rpb24gcGF0Y2hGZXRjaCgpIHtcbiAgICByZXR1cm4gX3BhdGNoRmV0Y2goe1xuICAgICAgICB3b3JrQXN5bmNTdG9yYWdlLFxuICAgICAgICB3b3JrVW5pdEFzeW5jU3RvcmFnZVxuICAgIH0pO1xufVxuZXhwb3J0IHsgcm91dGVNb2R1bGUsIHdvcmtBc3luY1N0b3JhZ2UsIHdvcmtVbml0QXN5bmNTdG9yYWdlLCBzZXJ2ZXJIb29rcywgcGF0Y2hGZXRjaCwgIH07XG5cbi8vIyBzb3VyY2VNYXBwaW5nVVJMPWFwcC1yb3V0ZS5qcy5tYXAiXSwibmFtZXMiOltdLCJpZ25vcmVMaXN0IjpbXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fauth%2Fsignin%2Froute&page=%2Fapi%2Fauth%2Fsignin%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fauth%2Fsignin%2Froute.ts&appDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!\n");

/***/ }),

/***/ "(rsc)/./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true!":
/*!******************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true! ***!
  \******************************************************************************************************/
/***/ (() => {



/***/ }),

/***/ "(ssr)/./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true!":
/*!******************************************************************************************************!*\
  !*** ./node_modules/next/dist/build/webpack/loaders/next-flight-client-entry-loader.js?server=true! ***!
  \******************************************************************************************************/
/***/ (() => {



/***/ }),

/***/ "../app-render/after-task-async-storage.external":
/*!***********************************************************************************!*\
  !*** external "next/dist/server/app-render/after-task-async-storage.external.js" ***!
  \***********************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/after-task-async-storage.external.js");

/***/ }),

/***/ "../app-render/work-async-storage.external":
/*!*****************************************************************************!*\
  !*** external "next/dist/server/app-render/work-async-storage.external.js" ***!
  \*****************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/work-async-storage.external.js");

/***/ }),

/***/ "./work-unit-async-storage.external":
/*!**********************************************************************************!*\
  !*** external "next/dist/server/app-render/work-unit-async-storage.external.js" ***!
  \**********************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/server/app-render/work-unit-async-storage.external.js");

/***/ }),

/***/ "buffer":
/*!*************************!*\
  !*** external "buffer" ***!
  \*************************/
/***/ ((module) => {

"use strict";
module.exports = require("buffer");

/***/ }),

/***/ "crypto":
/*!*************************!*\
  !*** external "crypto" ***!
  \*************************/
/***/ ((module) => {

"use strict";
module.exports = require("crypto");

/***/ }),

/***/ "mongoose":
/*!***************************!*\
  !*** external "mongoose" ***!
  \***************************/
/***/ ((module) => {

"use strict";
module.exports = require("mongoose");

/***/ }),

/***/ "next/dist/compiled/next-server/app-page.runtime.dev.js":
/*!*************************************************************************!*\
  !*** external "next/dist/compiled/next-server/app-page.runtime.dev.js" ***!
  \*************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/compiled/next-server/app-page.runtime.dev.js");

/***/ }),

/***/ "next/dist/compiled/next-server/app-route.runtime.dev.js":
/*!**************************************************************************!*\
  !*** external "next/dist/compiled/next-server/app-route.runtime.dev.js" ***!
  \**************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/compiled/next-server/app-route.runtime.dev.js");

/***/ }),

/***/ "stream":
/*!*************************!*\
  !*** external "stream" ***!
  \*************************/
/***/ ((module) => {

"use strict";
module.exports = require("stream");

/***/ }),

/***/ "util":
/*!***********************!*\
  !*** external "util" ***!
  \***********************/
/***/ ((module) => {

"use strict";
module.exports = require("util");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../../../webpack-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = __webpack_require__.X(0, ["vendor-chunks/next","vendor-chunks/ms","vendor-chunks/semver","vendor-chunks/jsonwebtoken","vendor-chunks/jws","vendor-chunks/ecdsa-sig-formatter","vendor-chunks/bcryptjs","vendor-chunks/safe-buffer","vendor-chunks/lodash.once","vendor-chunks/lodash.isstring","vendor-chunks/lodash.isplainobject","vendor-chunks/lodash.isnumber","vendor-chunks/lodash.isinteger","vendor-chunks/lodash.isboolean","vendor-chunks/lodash.includes","vendor-chunks/jwa","vendor-chunks/buffer-equal-constant-time"], () => (__webpack_exec__("(rsc)/./node_modules/next/dist/build/webpack/loaders/next-app-loader/index.js?name=app%2Fapi%2Fauth%2Fsignin%2Froute&page=%2Fapi%2Fauth%2Fsignin%2Froute&appPaths=&pagePath=private-next-app-dir%2Fapi%2Fauth%2Fsignin%2Froute.ts&appDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend%2Fapp&pageExtensions=tsx&pageExtensions=ts&pageExtensions=jsx&pageExtensions=js&rootDir=%2FUsers%2Fdakshjain%2FCODES%2FAI_Docx%2Ffrontend&isDev=true&tsconfigPath=tsconfig.json&basePath=&assetPrefix=&nextConfigOutput=&preferredRegion=&middlewareConfig=e30%3D!")));
module.exports = __webpack_exports__;

})();