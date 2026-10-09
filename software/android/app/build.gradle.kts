plugins {
    alias(libs.plugins.android.application)
    // Van can rieng plugin nay du AGP da tich hop Kotlin:
    // "Starting in Kotlin 2.0, the Compose Compiler Gradle plugin is required when compose is enabled"
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "vn.epcb.toydrone"
    // SDK 37 = Android 17; thu muc platform da cai tren may nay la android-37.0
    compileSdk = 37

    defaultConfig {
        applicationId = "vn.epcb.toydrone"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }
}

// Khong khai kotlin.compilerOptions.jvmTarget: voi Kotlin tich hop cua AGP, no mac dinh
// lay theo android.compileOptions.targetCompatibility (= 17 o tren).

dependencies {
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    debugImplementation(libs.androidx.compose.ui.tooling)

    // Driver USB-serial cho CH340 cua AK Base Kit 2.1 (cung ho tro CP210x, FTDI, CDC-ACM)
    implementation(libs.usbserial)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}
