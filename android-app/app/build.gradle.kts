plugins {
    id("com.android.application")
}

android {
    namespace = "com.mukasanches.ascension"
    compileSdk = 37
    ndkVersion = "30.0.16248370"

    defaultConfig {
        applicationId = "com.mukasanches.ascension"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0.0"

        ndk {
            abiFilters += listOf("arm64-v8a")
        }

        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DASCENSION_SDL2_SOURCE_DIR=${rootDir}/third_party/SDL",
                    "-DANDROID_STL=c++_shared"
                )
                cppFlags += listOf("-std=gnu++20")
                cFlags += listOf("-std=gnu11")
                targets += listOf("ascension", "SDL2")
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("${rootDir}/../android/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    sourceSets {
        getByName("main") {
            java.srcDir("${rootDir}/third_party/SDL/android-project/app/src/main/java")
        }
    }

    buildTypes {
        getByName("debug") {
            isJniDebuggable = true
        }
        getByName("release") {
            isMinifyEnabled = false
            ndk.debugSymbolLevel = "SYMBOL_TABLE"
        }
    }

    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
        resources {
            excludes += setOf("META-INF/**")
        }
    }
}
